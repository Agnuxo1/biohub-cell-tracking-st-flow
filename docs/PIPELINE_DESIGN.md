# ST-Flow: diseño técnico

## 1. Requisitos y decisiones

La entrada es un volumen `uint16` con forma habitual `(T, Z, Y, X)` y chunks por timepoint.
La escala física es `(1.625, 0.40625, 0.40625)` µm/voxel; por tanto, toda distancia,
vecindad y coste de linking se calcula en micras, nunca en distancia euclídea de voxeles.

La métrica oficial prioriza `adjusted_edge_jaccard` y sólo pondera divisiones con `0.1`.
Además, las etiquetas son dispersas y el exceso de nodos penaliza. De ahí se derivan cuatro
reglas operativas:

1. Mantener recall de candidatos, pero no forzar todos los candidatos dentro de tracks.
2. Resolver el linking como una decisión global con costes de aparición/desaparición.
3. Convertir la detección en una decisión temporal: una señal aislada pesa menos que una
   señal que reaparece en la trayectoria esperada.
4. Emitir divisiones sólo cuando aumentan la probabilidad de una arista correcta.

## 2. Flujo de datos

```text
┌───────────────┐
│ OME-Zarr      │  un timepoint por lectura
└──────┬────────┘
       ▼
┌───────────────────────────┐
│ Preprocesado físico        │  percentiles, fondo, sigma por eje
└──────┬────────────────────┘
       ▼
┌───────────────────────────┐
│ Propuestas 3D multiescala  │  DoG anisotrópico + máximos locales
└──────┬────────────────────┘
       ▼
┌───────────────────────────┐
│ Consenso temporal          │  soporte t-1/t/t+1, correlación de parche
└──────┬────────────────────┘
       ▼
┌───────────────────────────┐
│ Grafo candidato            │  nodos y aristas en µm, máximo 2 frames
└──────┬────────────────────┘
       ▼
┌───────────────────────────┐
│ Linker global              │  min-cost flow; Hungarian fallback
└──────┬────────────────────┘
       ▼
┌───────────────────────────┐
│ Poda + división 1→2        │  track quality y geometría
└──────┬────────────────────┘
       ▼
┌───────────────────────────┐
│ CSV oficial                │  nodos y edges agrupados por dataset
└───────────────────────────┘
```

## 3. Detección ST-Flow

### 3.1 Normalización y escalas

Para cada timepoint se calcula una normalización robusta con percentiles bajos/altos. El
background se estima con una apertura o un Gaussian blur de radio grande y se resta antes de
la detección. Los filtros usan sigmas físicos convertidos por eje:

```text
sigma_voxel = sigma_um / (1.625, 0.40625, 0.40625)
```

No se re-muestrea todo el vídeo a voxeles isotrópicos: se conserva el formato de entrada y se
aplica la anisotropía directamente, reduciendo memoria y tiempo.

### 3.2 Propuestas

Para cada escala `sigma_um ∈ {0.75, 1.10, 1.55}` se calcula una respuesta DoG/LoG 3D. Se
conservan máximos locales por encima de un umbral relativo al MAD del timepoint. Cada candidato
se refina con un ajuste parabólico local en `(z,y,x)` y queda representado como:

```text
(t, z, y, x, response, intensity, local_contrast, scale, border_distance)
```

Los candidatos de escalas próximas se fusionan en coordenadas físicas; el de mayor respuesta
se conserva y el resto alimenta un contador de doblete.

### 3.3 Consenso temporal

Un candidato se puntúa con tres evidencias:

```text
candidate_score =
    0.45 * spatial_response
  + 0.25 * patch_contrast
  + 0.20 * temporal_support
  + 0.10 * scale_consistency
```

`temporal_support` no exige que exista una detección exacta en el frame vecino: busca el mejor
parche dentro de una ventana física y mide correlación normalizada después de compensar el
desplazamiento mediano local. Esto permite mantener células que pierden intensidad un frame sin
convertir ruido persistente en nodos.

En el conjunto de entrenamiento se puede ajustar un pequeño clasificador PU (positive-unlabeled)
con parches 3D de 15–25 voxeles anisotrópicos. No se debe tratar lo no anotado como background,
porque la anotación es parcial. En el notebook de inferencia el clasificador, si se usa, debe
venir adjunto como dataset Kaggle; el pipeline funciona sin él usando el score determinista.

## 4. Grafo de candidatos y linking

### 4.1 Aristas

Se crean aristas `t→t+1` y sólo para casos con evidencia de oclusión, `t→t+2`. La compuerta es
elíptica en coordenadas físicas:

```text
||Δ_um - v_pred_um||_W ≤ gate_um
```

`v_pred` es velocidad constante estimada del track parcial; al inicio se usa la mediana local
del desplazamiento. El coste inicial recomendado es:

```text
edge_cost =
    1.00 * (distance_um / gate_um)^2
  + 0.35 * appearance_delta
  + 0.25 * motion_residual
  + 0.20 * (1 - min(score_src, score_dst))
```

La arista `t→t+2` lleva un coste extra de gap y sólo puede ganar si evita dos births/deaths.

### 4.2 Solver

Backend preferido: min-cost flow/ILP sobre el vídeo completo, con límites `max_parent=1` y
`max_child=1` antes de la fase de división. El nodo tiene recompensa configurable, no infinita:
así el solver puede descartar un doblete o un pico espurio en lugar de romper un track largo.

Fallback CPU: Hungarian por parejas de frames con memoria de track, seguido de una fase de
reconciliación de conflictos. Este fallback es menos global, pero sirve para producir una
submission válida cuando `motile`/`ultrack` no estén adjuntos.

### 4.3 Poda orientada a métrica

Después del solver se eliminan, en este orden:

1. nodos con score bajo que no pertenecen a ningún track de longitud `min_track_len`;
2. uno de dos nodos a menos de `doublet_radius_um` cuando ambos compiten por la misma arista;
3. saltos con residuo de movimiento alto;
4. segmentos cortos que sólo añaden births/deaths y ninguna arista confiable.

La constante de penalización de nodos se calibra en validación, no con una suposición sobre la
densidad absoluta del embrión. El objetivo de CV es mantener `N_pred/N_estimated` cerca de 1,
pero el test no debe depender de ground truth oculto.

## 5. Divisiones

Una división candidata `p → {c1,c2}` exige:

- dos hijos en `t+1` o `t+2` dentro de la compuerta;
- una separación física de hijas dentro de un rango aprendido en train;
- suma de costes menor que mantener un solo hijo y crear un birth adicional;
- soporte de intensidad compatible en el parche de la madre y de las hijas.

Si varias divisiones compiten, se conserva la de mayor margen. El modo por defecto es
conservador: es preferible perder alguna división a introducir dos aristas incorrectas que
contaminen el Jaccard principal.

## 6. Calibración y validación

La validación local debe ser por embrión: nunca mezclar frames de `44b6` y `6bba` en el mismo
fold. Cada experimento guarda:

```text
candidate_recall, node_ratio, edge_jaccard, adjusted_edge_jaccard,
division_jaccard, runtime_seconds, peak_memory_mb
```

Orden de tuning recomendado:

1. `gate_um`, `min_track_len`, recompensa de nodo;
2. umbral de candidato y supresión de dobletes;
3. coste de gap y memoria de velocidad;
4. umbral de división.

No se debe seleccionar el modelo por division Jaccard aislado. El criterio principal es
`adjusted_edge_jaccard` agregado y estabilidad entre ambos embriones.

## 7. Presupuesto de ejecución Kaggle

- Leer por chunks de tiempo; no materializar el vídeo completo.
- Guardar sólo candidatos compactos (`float32`) y aristas dispersas.
- Ejecutar la detección por lotes de timepoints si hay GPU; el linker usa CPU y estructuras
  dispersas.
- Registrar tiempo por dataset y cortar cualquier rama experimental si el ETA supera 10 h,
  reservando margen para serialización y escritura.
- Adjuntar todos los wheels/modelos usados; el scoring corre sin Internet.

## 8. Riesgos y mitigaciones

| Riesgo | Señal | Mitigación |
|---|---|---|
| Anisotropía mal aplicada | demasiados vecinos en Z o tracks zigzagueantes | todas las compuertas en µm; test sintético anisotrópico |
| Sobre-detección | `node_ratio` alto, tracks cortos | reward de nodo finito, supresión de dobletes |
| Fragmentación | mediana de track baja | gap `t→t+2`, coste de birth/death calibrado |
| Divisiones falsas | sube división, cae edge Jaccard | activar sólo con margen y soporte de parche |
| Timeout | ETA > 10 h | detector determinista, fallback Hungarian, no Cellpose-SAM por defecto |
| Error de schema | CSV rechazado | validador de columnas, ids consecutivos, dataset completo |

## 9. Criterios de aceptación

1. El test de humo construye un grafo anisotrópico y verifica que el matching no confunde Z con
   XY.
2. Un input sintético con dos tracks y una división produce nodos/edges válidos.
3. El escritor genera exactamente las columnas oficiales y ids consecutivos.
4. En un fold local, el pipeline supera al baseline de nearest-neighbour en edge Jaccard o,
   si no lo hace, la decisión queda documentada antes de activar modelos pesados.
5. En Kaggle, cada dataset de test aparece y se escribe `/kaggle/working/submission.csv`.

