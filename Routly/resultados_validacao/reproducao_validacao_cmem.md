# Reprodução do registro `docs/validacao_cmem.json`

Registro de 2026-09-09: R. AMADEU ASSAD YASSIM → R. GEN. LUIZ CARLOS PEREIRA TOURINHO, CMEM com o perfil histórico `hdv-generico` (13000 kg de massa vazia). Tolerância relativa 1e-09.

**16/16 verificações reproduzidas.**

| Verificação | Registrado | Obtido | Resultado |
|---|---|---|---|
| SHA-256 do grafo | 3037976cef04594a937ec581be2e452474c929d46f41463facdae166063c7979 | 3037976cef04594a937ec581be2e452474c929d46f41463facdae166063c7979 | OK |
| Distância (m) — distancia, 0 kg, 30 km/h | 28831.870000 | 28831.870000 | OK |
| CO₂ (g) — distancia, 0 kg, 30 km/h | 29944.976224 | 29944.976224 | OK |
| Custo Dijkstra — distancia, 0 kg, 30 km/h | 28831.870000 | 28831.870000 | OK |
| Distância (m) — emissao, 0 kg, 30 km/h | 30441.710000 | 30441.710000 | OK |
| CO₂ (g) — emissao, 0 kg, 30 km/h | 29359.052256 | 29359.052256 | OK |
| Custo Dijkstra — emissao, 0 kg, 30 km/h | 29359.052256 | 29359.052256 | OK |
| Distância (m) — distancia, 10000 kg, 30 km/h | 28831.870000 | 28831.870000 | OK |
| CO₂ (g) — distancia, 10000 kg, 30 km/h | 38759.637183 | 38759.637183 | OK |
| Custo Dijkstra — distancia, 10000 kg, 30 km/h | 28831.870000 | 28831.870000 | OK |
| Distância (m) — emissao, 10000 kg, 30 km/h | 30792.590000 | 30792.590000 | OK |
| CO₂ (g) — emissao, 10000 kg, 30 km/h | 36850.056700 | 36850.056700 | OK |
| Custo Dijkstra — emissao, 10000 kg, 30 km/h | 36850.056700 | 36850.056700 | OK |
| BOA* carga 0: nº de alternativas | 39 | 39 | OK |
| BOA* carga 0: extremo de distância (m) | 28831.870000 | 28831.870000 | OK |
| BOA* carga 0: extremo de emissão (g) | 29359.052256 | 29359.052256 | OK |

Nota do registro: Estimativas de cenário sem calibração local; tempos de uma execução, não benchmark estatístico.

A igualdade dos custos verifica a busca (ALT = Dijkstra, resultados estáveis), não a precisão física da estimativa de emissão.
