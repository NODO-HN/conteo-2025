# Metodología: Análisis Electoral 5 de Diciembre

**Fecha:** 5 de Diciembre, 2025
**Asunto:** Justificación de la Estrategia de Visualización y Proyección

## 1. Resumen Ejecutivo

Este documento detalla la metodología detrás de las proyecciones y visualizaciones electorales generadas en este repositorio.

**El Enfoque:** Visualizamos el **Volumen Estimado Restante (~25%)** de forma prominente, comparándolo con el **margen entre candidatos (~20K votos)**.

**La Razón:** En resultados electorales parciales, el riesgo principal es el **sesgo sistemático** (ej. regiones específicas que reportan tarde). No calculamos un "margen de error estadístico" porque:

1. **No tenemos datos a nivel de acta individual** - solo agregados departamentales
2. **Las actas contadas no son una muestra aleatoria** - son las que se transmitieron primero
3. **La incertidumbre real es el sesgo**, no la varianza de muestreo

Nuestra visualización destaca la *magnitud de la estimación* (el volumen de votos proyectados vs. reportados), que es el enfoque honesto.

---

## 2. Metodología de Proyección

### Datos Disponibles

Para cada departamento, tenemos:
- **Votos reportados** por candidato (de actas correctas)
- **Número de actas**: totales, divulgadas, correctas, inconsistentes

**No tenemos**: Votos individuales por acta/JRV, lo cual impide calcular varianza observada.

### Cálculo de Proyecciones

Para cada departamento $h$:

1. **Actas restantes:**
   $$R_h = \text{actas faltantes} + \text{actas inconsistentes}$$

2. **Votos promedio por acta correcta:**
   $$\bar{v}_h = \frac{\text{votos válidos}_h}{\text{actas correctas}_h}$$

3. **Votos restantes estimados:**
   $$\hat{V}_{restante,h} = R_h \times \bar{v}_h$$

4. **Distribución proporcional:** Los votos restantes se asignan a cada candidato según su participación actual en el departamento.

### El Supuesto Clave

> Las actas restantes de cada departamento votarán en proporciones similares a las actas ya contadas de ese mismo departamento.

**Este supuesto no es verificable con los datos disponibles.** Si las actas faltantes provienen de zonas con preferencias distintas (ej. rural vs. urbano), la proyección será incorrecta.

---

## 3. Estrategia de Visualización

Elegimos visualizar el volumen estimado para ser transparentes sobre la incertidumbre estructural.

1. **Honestidad sobre la incertidumbre:** Con ~25% de votos estimados y un margen de ~20K votos, el resultado depende completamente de cómo voten las actas pendientes.

2. **Etiquetado claro:** Las gráficas muestran explícitamente "Est." en las áreas rayadas para distinguir votos reportados de estimados.

3. **Sin falsa precisión:** No reportamos intervalos de confianza porque no tenemos los datos necesarios para calcularlos correctamente.

---

## 4. Limitaciones

| Limitación | Impacto |
|------------|---------|
| Solo datos agregados por departamento | No podemos medir variación real entre actas |
| Actas contadas no son muestra aleatoria | No se aplican fórmulas de muestreo estándar |
| Razones de inconsistencia desconocidas | Podrían correlacionar con preferencias políticas |
| Sin validación histórica | No sabemos qué tan bien funciona el supuesto |

**Conclusión:** Este análisis es útil para visualizar la magnitud de la incertidumbre, pero no para predecir el resultado con confianza.
