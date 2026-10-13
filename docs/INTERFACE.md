# Interface do Routly

O painel local reúne os motores e experimentos existentes, sem substituir o menu do terminal.
É servido apenas em `127.0.0.1` e não exige Node.js, serviços externos ou novas bibliotecas de interface.

A navegação inclui transições curtas nos grupos, cartões, abas e janelas. Novas execuções entram
suavemente na fila e seus estados mudam sem reconstruir o histórico ou perder o foco do teclado.
As animações e a rolagem suave respeitam a preferência de movimento reduzido do sistema.

Cada cartão oferece o botão **O que este teste comprova?**, com um guia específico sobre
o objetivo, o procedimento, a interpretação dos resultados e os limites da conclusão.
A explicação abre sem executar a operação; pode ser fechada por **Entendi**, pelo botão
de fechar ou pela tecla Esc. Os textos distinguem verificações automáticas, análises de
modelos e inspeções visuais. Novos módulos de teste descobertos automaticamente recebem
uma orientação geral até ganharem um texto específico em `interface/static/explicacoes.js`.

## Iniciar no Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe interface.py
```

No Linux/macOS, use `.venv/bin/python` nos dois últimos comandos.
O navegador abre em `http://127.0.0.1:8765`. Para mudar a porta ou evitar a abertura automática:

```powershell
.\.venv\Scripts\python.exe interface.py --porta 8766 --sem-abrir
```

Também é possível iniciar pelo menu: `python main.py --interface`.

## Grupos e cobertura do terminal

| Grupo | Operações |
|---|---|
| Testes automatizados | pytest completo, unittest e cada arquivo `tests/test_*.py`, descoberto automaticamente |
| Validação de modelos | Conversão CO₂, paridade física, reprodução CMEM, eficácia em três camadas e validação integrada (3.1) |
| Análises científicas | Pareto (3.3), perfil altimétrico (3.4), Monte Carlo/Wilcoxon (3.5) e pipeline completo (3.6) |
| Roteamento | ALT distância/emissão, BOA* e NBA*, com modelos VT-CPFM/CMEM/legado, cargas, velocidade, landmarks e alternativa de rota |
| Dados e mapas | ETL (1.1), mapa Leaflet (1.2), cruzamentos (1.3), visualização do grafo e diagnóstico dos shapefiles/nomes |

Os formulários substituem as perguntas dos assistentes interativos. Os parâmetros de roteamento do
`executar.py` estão disponíveis em campos tipados; não há execução de comandos shell livres.
O botão **Executar grupo** enfileira as operações individuais e permite configurar seus parâmetros
compartilhados. Suítes agregadas, validação integrada, pipeline completo e ETL ficam fora do lote
para evitar duplicações e recriações demoradas. Continuam disponíveis em seus próprios cartões.

O pipeline completo mantém os padrões de `rodar_tudo` do terminal: eficácia com 100 pares, cenário
carregado e 21 passos de α. O campo de pares do pipeline controla o Monte Carlo. Para configurar
esses experimentos individualmente, use seus cartões.

## Resultados e histórico

- Cada execução roda em um processo Python separado, usando o mesmo interpretador do servidor.
- A fila executa uma tarefa por vez. **Cancelar** encerra o processo e seus subprocessos ou remove a tarefa da fila.
- O terminal captura stdout e stderr, incluindo erros. A tela mostra os últimos 256 KiB; o download contém o log inteiro.
- Gráficos Matplotlib são exportados para PNG; mapas HTML são exibidos em um iframe isolado, com a malha local IPPUC. A biblioteca Leaflet é carregada pela internet; o mapa-base externo é opcional no controle de camadas.
- CSVs têm uma prévia de até 200 registros, com download completo. JSON, Markdown e texto também têm visualização e download.
- Os arquivos ficam em `.routly/runs/<id>/`, ignorado pelo Git. Ao reiniciar, execuções pendentes são marcadas como interrompidas, sem retomada automática.
- **Resultados salvos** abre os arquivos de referência de `resultados_validacao/`, identificados separadamente das novas execuções.
- O ETL exporta seu CSV para a pasta da execução. Para adotá-lo, copie-o para `grafo_curitiba_carbono.csv` na raiz do projeto.

Sem grafo ou shapefiles, as operações correspondentes informam a falta de dados. GeoPandas só é
necessário para ETL/inspeção dos shapefiles; as demais dependências científicas estão em `requirements.txt`.
O painel mostra essas ausências e preserva as mensagens de erro do motor. Uma execução concluída
indica término sem erro de processo; não implica validação empírica do modelo de emissões.

## Estrutura e verificação

`interface/catalogo.py` define operações e valida parâmetros; `interface/worker.py` adapta os
motores existentes; `interface/servidor.py` gerencia HTTP, histórico, fila e cancelamento.
`interface/static/` contém HTML, CSS e JavaScript responsivos, sem dependências de CDN.

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Os testes da interface verificam descoberta de suítes, parâmetros, exportação de figuras,
propagação de falhas, ordem da fila, cancelamento, persistência e restrições de acesso aos arquivos.
