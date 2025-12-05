# Metodología Estadística: Análisis Electoral 5 de Diciembre

**Fecha:** 5 de Diciembre, 2025
**Asunto:** Justificación de la Estrategia de Visualización y Proyección

## 1. Resumen Ejecutivo

Este documento detalla la metodología detrás de las proyecciones y visualizaciones electorales generadas en este repositorio.

**El Enfoque:** Elegimos visualizar el **Volumen Estimado Restante (~25%)** junto con un **Margen de Error Estadístico (±0.4%)** calculado rigurosamente.

**La Razón:** En resultados electorales parciales, el riesgo principal es el **sesgo sistemático** (ej. regiones específicas que reportan tarde), no el **error de muestreo aleatorio**. Mostrar solo un margen de error estadístico pequeño (±0.4%) sería matemáticamente correcto pero engañoso, ya que ignora el potencial de sesgo en los votos no contados. Nuestra visualización destaca la *magnitud de la suposición* (el volumen estimado), que es el enfoque honesto y profesional.

---

## 2. El Análisis: Verificación de Sanidad Estadística

Para determinar el enfoque correcto, realizamos una "verificación de sanidad" estadística rigurosa.

### Metodología: Muestreo Aleatorio Estratificado
Modelamos los resultados electorales utilizando **Muestreo Aleatorio Estratificado con Corrección de Población Finita (FPC)**.
*   **Estratos:** Cada uno de los 18 Departamentos se trató como un estrato distinto.
*   **Población Finita:** Contabilizamos el hecho de que estamos contando un número fijo de "Actas". A medida que el conteo se acerca al 100%, el error naturalmente se reduce a cero.

**La Fórmula:**
Calculamos la varianza de los votos totales proyectados para el candidato líder:
$$ Var(Total) = \sum N_h^2 (1 - f_h) \frac{S_h^2}{n_h} $$
*   $N_h$: Total de Actas en el Departamento $h$
*   $f_h$: Fracción de Actas ya contadas en el Departamento $h$
*   $n_h$: Número de Actas contadas en el Departamento $h$
*   $S_h^2$: Varianza de votos dentro del Departamento $h$

### Los Hallazgos

| Métrica | Valor | Definición |
| :--- | :--- | :--- |
| **Volumen Estimado Restante** | **~25.0%** | El porcentaje de votos que actualmente no están contados y están siendo "rellenados" por nuestro modelo de proyección. |
| **Margen de Error Estadístico (IC 95%)** | **±0.40%** | El rango puramente matemático de error, asumiendo que los votos no contados son una muestra *aleatoria* de sus departamentos. |

---

## 3. Estrategia de Visualización

Elegimos visualizar el volumen estimado para ser transparentes sobre la incertidumbre estructural.

1.  **Honestidad sobre Precisión:** En un escenario con ~25% de datos faltantes, la "Precisión" (±0.4%) es menos valiosa que la "Transparencia" sobre el volumen de datos faltantes.
2.  **Etiquetado Claro:** Las gráficas muestran explícitamente "Est." (Volumen Estimado) en las áreas rayadas.
3.  **Contexto Textual:** Incluimos el MoE estadístico (±0.40%) en las etiquetas para satisfacer el rigor técnico sin engañar al lector visual sobre el riesgo de sesgo.

**Supuesto Clave:**
La proyección asume que las actas restantes seguirán los patrones de votación observados actualmente dentro de cada departamento.
