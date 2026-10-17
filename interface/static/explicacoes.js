/* Guias de leitura das operações, baseados nos testes e motores do projeto. */
const explicacoes = {
  comparacao_rotas: [
    'Compara a rota de menor distância com a de menor custo de carbono e mostra como a subida acumulada difere entre elas.',
    'Usa os custos já presentes no CSV do grafo e sorteia até 50 pares na maior componente fortemente conexa. Encerra ao encontrar duas rotas diferentes, calculadas com NetworkX.',
    'Consulte o Terminal para ver origem, destino, ruas, distância, subida acumulada e CO₂ de cada rota, além das diferenças entre elas. Esta operação não gera gráficos ou tabelas de arquivos.',
    'Os pontos são aleatórios e podem mudar a cada execução. Se as 50 tentativas produzirem rotas iguais, o Terminal informa isso. Um exemplo encontrado não demonstra economia para toda a malha nem comprova emissões medidas em campo.'
  ],
  testes_todos: [
    'Verifica em conjunto os comportamentos cobertos pelos testes do Routly: algoritmos de busca, modelos de emissão, unidades, cenários, análises científicas e interface.',
    'Executa o pytest sobre a pasta tests/. Cada caso compara o resultado obtido com uma condição esperada, como um custo ótimo conhecido, uma equação calculada separadamente ou uma regra de funcionamento da fila.',
    'Consulte o Terminal: PASSED indica uma verificação aprovada; FAILED ou ERROR precisa de investigação; SKIPPED indica que a verificação não foi executada. Leia também os motivos dos testes ignorados.',
    'Uma suíte aprovada indica ausência de regressões nos casos executados. Não cobre todas as entradas possíveis nem comprova que as emissões calculadas correspondem a medições de um veículo real.'
  ],
  unittest: [
    'Verifica os casos compatíveis com unittest descobertos na pasta tests/, usando o executor padrão do Python.',
    'Descobre as classes de teste e executa suas verificações, incluindo os subtestes definidos nelas. É uma alternativa para conferir os contratos do projeto pelo mesmo mecanismo disponível no terminal.',
    'No Terminal, confira a quantidade de testes, o resultado OK e os registros de falha, erro ou skip. OK com testes ignorados não significa que esses casos foram aprovados.',
    'A descoberta do unittest não executa necessariamente todos os formatos aceitos pelo pytest. O resultado vale para os casos efetivamente descobertos e executados.'
  ],
  teste_algoritmos: [
    'Verifica se ALT e BOA* encontram os custos esperados em pequenos grafos dirigidos, incluindo situações difíceis de busca.',
    'Compara as respostas com a enumeração exaustiva de caminhos. Confere mínimos de distância e emissão, alternativas de Pareto, empates, ciclos, arestas paralelas, origem igual ao destino, ausência de caminho e rejeição de custos inválidos.',
    'Todos os casos devem passar. Uma falha pode indicar que uma rota ótima foi perdida, uma alternativa dominada foi mantida ou uma entrada inválida foi aceita.',
    'É uma verificação de correção nos grafos de teste, não um benchmark de velocidade nem uma validação das emissões físicas. Este conjunto não certifica o algoritmo legado NBA*.'
  ],
  teste_cenarios_co2: [
    'Verifica se a escolha do fator de conversão de combustível para CO₂ muda a escala das emissões sem alterar indevidamente o consumo, a potência ou as rotas.',
    'Compara os cenários EPA e artigo no VT-CPFM, as buscas e a fronteira de Pareto. Exercita os argumentos do terminal, os padrões do menu, combinações incompatíveis e o carregamento do catálogo no modelo legado.',
    'Os casos devem confirmar consumo e potência iguais, CO₂ proporcional ao fator escolhido e preservação das rotas nos exemplos. Falhas apontam uma inconsistência na aplicação ou seleção do cenário.',
    'A preservação da rota decorre da multiplicação uniforme dos custos por um fator positivo. Isso não demonstra qual fator representa melhor um veículo nem reproduz as medições do artigo.'
  ],
  teste_comprovacao: [
    'Verifica a infraestrutura que produz as análises científicas: busca ponderada, fronteira de compromisso, estatística, gráficos, relatórios e integração com o menu.',
    'Compara extremos da busca com Dijkstra, confere que a heurística preserva o ótimo, verifica a solução próxima do ponto ideal e confronta soluções com BOA*. Também testa Wilcoxon, conversão de coordenadas, exportação de arquivos e reprodução do registro CMEM.',
    'A aprovação indica que esses cálculos e fluxos satisfazem as condições dos casos de teste. O Terminal identifica a etapa exata quando uma comparação ou exportação falha.',
    'O nome “comprovação científica” identifica o módulo testado. A aprovação desta suíte, por si só, não é uma comprovação experimental da economia de combustível no trânsito real.'
  ],
  teste_conversao_co2: [
    'Verifica a consistência das unidades e do processamento usado para transformar consumo de combustível em emissões de CO₂.',
    'Testa conversões de L/100 km para L/km e g/km, integração de uma vazão controlada, filtro de registros diesel, rejeição de dados inválidos, estatísticas e exportações. O download e o cache são exercitados com respostas simuladas.',
    'Todos os casos devem passar. Divergências podem revelar fator de escala errado, dados inválidos incluídos na amostra ou problemas na leitura e geração dos relatórios.',
    'A aprovação verifica a implementação e seus exemplos controlados. Os testes de download simulados não garantem disponibilidade do serviço externo; unidades corretas não garantem calibração física do modelo.'
  ],
  teste_eficacia: [
    'Verifica se a economia estimada das rotas ecológicas permanece consistente em uma amostra fixa da malha de Curitiba e se houve regressão nos resultados.',
    'Usa 20 pares com semente fixa, veículo vazio e 20.000 kg adicionais. Exige economia média superior a 1,5% e 5%, respectivamente, p < 0,01 no cenário pesado e economia média superior a 3% quando as rotas são reavaliadas pelo CMEM. Também compara três rotas com Dijkstra.',
    'Todos os critérios devem passar: existência de rotas, custos coerentes, limites mínimos de economia e concordância com a referência. Sem o CSV do grafo, os testes da malha são ignorados.',
    'Os limites são critérios de regressão desta amostra, não promessas para qualquer trajeto. A comparação usa emissões calculadas; não mede consumo em campo.'
  ],
  teste_emissoes: [
    'Verifica a implementação do modelo CMEM simplificado e sua integração aos custos das rotas.',
    'Compara consumo e CO₂ com equações independentes, confere efeitos de relevo e carga, consumo mínimo nas descidas, custo nulo para trecho de comprimento zero e preservação do custo ao dividir uma rampa uniforme. Exercita entradas inválidas, grafo reverso e caminhos alternativos.',
    'A aprovação confirma as relações e valores esperados nos exemplos. Uma rota mais longa pode ser escolhida quando seu custo de emissão calculado é menor.',
    'A concordância com as equações verifica o código do modelo simplificado. Não equivale à calibração do motor de um caminhão específico nem à validação com medições reais.'
  ],
  teste_vtcpfm: [
    'Verifica as equações do VT-CPFM e a formação dos custos de emissão usados pelos algoritmos de busca.',
    'Compara potência, combustível e CO₂ com um cálculo independente; testa regimes de potência, aceleração, altitude, carga, subidas e descidas. Confere alertas de potência excedida, entradas inválidas e custos direcionais na integração com ALT e BOA*.',
    'Todos os casos devem passar. A sinalização de potência excedida indica uma condição além da potência nominal do perfil; o teste verifica que essa condição é detectada.',
    'O resultado confirma o comportamento implementado nos cenários de teste. Não comprova que o veículo consegue manter a velocidade solicitada em qualquer rampa nem substitui medições de combustível.'
  ],
  teste_interface: [
    'Verifica os contratos do painel: parâmetros aceitos, execução em fila, resultados, cancelamento e acesso aos arquivos.',
    'Exercita descoberta de testes, rejeição de entradas inválidas, propagação de falhas, exportação de figuras, persistência e restrições de caminhos. Quando Node.js está disponível, inclui regressões de troca de execução e reabertura de arquivos no frontend.',
    'Confira os casos aprovados e eventuais skips no Terminal. Uma falha identifica um contrato da interface que deixou de ser atendido, mesmo que a página ainda abra.',
    'Os cenários automatizados não cobrem toda interação visual, navegador ou tamanho de tela. As regressões do frontend são ignoradas se o ambiente não tiver Node.js.'
  ],
  modelos: [
    'Reúne evidências sobre a consistência da conversão de CO₂, a eficácia estimada das rotas, a reprodução do CMEM e a concordância física entre modelos.',
    'Executa a validação de unidades e catálogo, a avaliação em três camadas, a reprodução do registro histórico CMEM e a comparação VT-CPFM × CMEM por declividade. O campo de pares controla a amostra da avaliação de eficácia.',
    'Leia os relatórios e as métricas de cada etapa. Verificações de unidades ou do registro CMEM reprovadas fazem esta operação falhar; a qualidade da economia e da paridade deve ser avaliada nos valores apresentados.',
    '“Concluído” não significa que todas as métricas científicas alcançaram um limiar de aprovação. A operação combina verificações e análises entre modelos, sem medir emissões de um caminhão real.'
  ],
  conversao: [
    'Verifica as unidades da conversão combustível → CO₂ e avalia a compatibilidade do fator adotado com registros diesel do catálogo canadense.',
    'Converte consumo em L/100 km para L/km, calcula emissões em g/km e estima fatores implícitos em g/L a partir dos dados do catálogo. Separa registros válidos e rejeitados e exporta estatísticas e relatório.',
    'Confira as verificações de unidades, a quantidade de registros aproveitados e a diferença entre o fator de referência e os fatores implícitos. O relatório permite distinguir um erro de unidade de uma diferença entre bases.',
    'A comparação avalia a conversão, não a capacidade do VT-CPFM de prever o consumo de caminhões. A composição e o arredondamento do catálogo influenciam os fatores estimados.'
  ],
  fisica: [
    'Avalia o quanto VT-CPFM e CMEM produzem respostas semelhantes às mudanças de declividade e carga sob condições controladas.',
    'Calcula os dois modelos em rampas de −6% a +6%, nos três cenários de carga, com velocidade e altitude fixadas pelo experimento. Produz curvas, pontos de referência e métricas globais e por cenário.',
    'Observe se as curvas acompanham os pontos CMEM e consulte R², MAPE e os demais erros no JSON. R² próximo de 1 e erros menores indicam maior concordância nas condições avaliadas; a execução não impõe um limiar universal de aprovação.',
    'O CMEM é uma referência calculada, não uma medição de campo. Dois modelos podem concordar e ainda compartilhar hipóteses ou desvios em relação ao veículo real.'
  ],
  cmem: [
    'Verifica se a implementação atual ainda reproduz os valores de referência registrados para o CMEM no projeto.',
    'Reexecuta as verificações descritas no registro histórico de validação e compara resultados atuais com os esperados, dentro da tolerância numérica definida pelo código.',
    'O relatório mostra quantas verificações passaram e as divergências encontradas. Esta operação termina com falha se a quantidade aprovada for diferente do total.',
    'É uma checagem de reprodução e regressão. Reproduzir um registro histórico não constitui uma nova validação experimental, nem garante que as hipóteses originais se apliquem a qualquer veículo.'
  ],
  eficacia: [
    'Investiga se escolher rotas pelo CO₂ estimado reduz emissões em relação à menor distância e se esse ganho resiste a mudanças de modelo e altitude.',
    'Sorteia pares com a semente informada e compara rotas nas cargas e velocidades escolhidas. A segunda camada reavalia rotas com CMEM, se habilitado; a terceira perturba altitudes com os desvios de ruído configurados.',
    'Leia economia média, intervalo de confiança, distância adicional e teste pareado. Compare o ganho no VT-CPFM com o ganho sob CMEM e ruído. Uma camada desabilitada não fornece evidência sobre essa dimensão.',
    'O resultado depende da amostra, da malha e dos parâmetros. Ganho sob o próprio modelo de otimização é esperado; a validação cruzada e o ruído ajudam a avaliar robustez, mas ainda não representam consumo medido.'
  ],
  pareto: [
    'Mostra o compromisso entre percorrer menos distância e emitir menos CO₂ para um par de ruas e um cenário de carga.',
    'Varia o peso α da busca ponderada e compara as soluções. Quando habilitado, BOA* calcula a fronteira exata de custos não dominados. A solução de compromisso é escolhida pela proximidade ao ponto ideal nos objetivos normalizados.',
    'No gráfico, uma alternativa é dominada se outra é tão boa ou melhor nos dois objetivos e estritamente melhor em pelo menos um. Observe a redução de CO₂ e a distância adicional da solução de compromisso em relação aos extremos.',
    'A varredura de α pode deixar de encontrar alternativas da fronteira; aumentar os passos não a torna automaticamente exata. O compromisso depende da regra de normalização e não é uma escolha universal para todo usuário.'
  ],
  perfil: [
    'Ajuda a explicar onde o relevo e os custos dos trechos diferenciam a rota mais curta da rota de menor emissão.',
    'Calcula as duas rotas para as ruas e a carga escolhidas, extrai a elevação ao longo do percurso e acumula o CO₂ estimado. O gráfico também destaca o início de aclives acima do limiar do experimento.',
    'Compare os perfis de altitude, os comprimentos e o crescimento do CO₂ acumulado. Uma curva de emissão que sobe mais rapidamente identifica trechos mais custosos dentro das hipóteses do modelo.',
    'É uma análise explicativa de um par de rotas. Não isola causalmente todos os fatores, não considera automaticamente trânsito real e depende da qualidade das altitudes do grafo.'
  ],
  monte_carlo: [
    'Avalia a distribuição da economia estimada em muitos pares de origem e destino, em vez de depender de um único exemplo favorável.',
    'Amostra pares com semente reproduzível nos cenários vazio, meia carga e carregado. Compara as rotas curta e ecológica, reavalia custos com CMEM e calcula Wilcoxon pareado, tamanho de efeito e intervalo de confiança de 95% da mediana por bootstrap.',
    'Leia boxplots, mediana, intervalo de confiança, tamanho de efeito e valores de p em conjunto. Um p pequeno indica evidência contra a hipótese nula do teste nas condições da amostra; não informa sozinho se a economia é relevante na prática.',
    'A inferência vale para o processo de amostragem e as hipóteses do experimento. As rotas compartilham uma malha e podem compartilhar trechos; significância estatística não demonstra economia real em campo nem valida a calibração do modelo.'
  ],
  pipeline: [
    'Consolida as evidências do fluxo científico do terminal em uma execução: consistência dos modelos, testes automatizados, compromisso entre objetivos, relevo e avaliação estatística.',
    'Executa as etapas 3.1 a 3.5 e gera um relatório final com métricas e arquivos. Origem e destino definem a análise ilustrativa; pares e semente configuram o Monte Carlo. As outras etapas mantêm seus padrões próprios.',
    'Use o relatório para conectar as conclusões de cada etapa e consulte os arquivos detalhados quando houver divergência. Falhas nos testes automatizados ou nas verificações obrigatórias dos modelos são propagadas para o estado da execução.',
    'A conclusão do pipeline não transforma todas as análises em testes aprovados. O relatório reúne evidências computacionais condicionadas aos modelos e dados; não representa uma campanha de medição real.'
  ],
  alt_distancia: [
    'Calcula uma rota de menor distância entre os pontos associados às ruas escolhidas, considerando os comprimentos armazenados no grafo.',
    'Usa A* com landmarks (ALT) para orientar a busca e soma distância e emissão dos trechos. Os parâmetros do veículo definem a emissão reportada, enquanto o objetivo desta operação permanece a distância.',
    'Confira a distância total, o CO₂ estimado e o percurso no terminal ou na imagem, quando solicitada. Para avaliar economia de CO₂, compare com ALT · menor emissão usando exatamente os mesmos parâmetros.',
    'Esta execução calcula uma solução; não faz, sozinha, uma comparação independente para provar a correção do algoritmo. O ótimo se refere ao grafo e aos pontos selecionados, não ao menor tempo de viagem nem a todas as condições reais da via.'
  ],
  alt_emissao: [
    'Calcula uma rota que minimiza a soma do CO₂ estimado nos trechos, de acordo com o modelo e o perfil escolhidos.',
    'Atribui custos de emissão ao grafo usando VT-CPFM, CMEM ou o modelo legado e aplica ALT ao objetivo emissão. Carga, velocidade e demais opções influenciam esses custos.',
    'Compare CO₂ e distância com a rota de menor distância, mantendo os mesmos parâmetros. Uma rota mais longa pode ter menor emissão estimada; também é possível que os dois objetivos escolham o mesmo caminho.',
    'É uma otimização dos custos calculados, não uma medição de CO₂. Com taxa uniforme por quilômetro no modelo legado, minimizar emissão equivale a minimizar distância. A execução isolada não verifica o ótimo contra uma referência independente.'
  ],
  boa: [
    'Identifica alternativas de custo não dominadas entre distância e emissão, permitindo escolher quanto percurso adicional aceitar por uma redução de CO₂.',
    'Executa BOA* no grafo com os parâmetros informados e lista a fronteira de Pareto. A opção de alternativa seleciona qual solução será detalhada e desenhada, se a geração de imagem estiver ativa.',
    'Compare os pares distância–emissão. Na fronteira, melhorar um objetivo exige piorar o outro. A alternativa selecionada é uma escolha para inspeção, não uma aprovação automática da melhor rota para todas as necessidades.',
    'A fronteira é exata para os custos e restrições representados no grafo; isso não torna exatas as emissões no mundo real. O cálculo pode ser demorado e não enumera necessariamente todos os caminhos com custos idênticos.'
  ],
  nba: [
    'Permite inspecionar o resultado do algoritmo bidirecional legado NBA* para o objetivo distância ou emissão.',
    'Executa buscas a partir dos extremos usando o motor legado e os custos do modelo escolhido. Apresenta o caminho e seus totais para o par de ruas configurado.',
    'Leia o percurso, a distância e a emissão no Terminal. Para investigar concordância entre motores, compare com ALT usando o mesmo objetivo, veículo, carga, velocidade, origem e destino.',
    'A execução deste cartão não faz essa comparação automaticamente nem certifica a otimalidade do motor legado. Resultados diferentes exigem investigação; tempo de execução isolado também não constitui um benchmark controlado.'
  ],
  mapa: [
    'Permite visualizar onde as rotas mais curta, ecológica e de compromisso coincidem ou se separam para as ruas e a carga escolhidas.',
    'Calcula as alternativas com os padrões do experimento e gera um HTML interativo sobre a malha do IPPUC. A rota de compromisso vem da busca ponderada; as camadas permitem comparar os percursos e seus valores.',
    'Abra mapa_rotas.html nos resultados, alterne as camadas e compare distância e CO₂ de cada alternativa. Observe se a redução estimada de emissão exige um desvio e se as rotas seguem os trechos representados na malha.',
    'O mapa é uma inspeção visual, sem critério automático de aprovação. Não prova, sozinho, a correção do algoritmo ou economia real. Os custos usam as hipóteses fixas do experimento, sem incorporar automaticamente trânsito e restrições de circulação atuais.'
  ],
  cruzamentos: [
    'Identifica ruas que compartilham pelo menos um nó com a rua informada na representação do grafo.',
    'Procura o nome da rua e compara as coordenadas de origem e destino de seus segmentos com os segmentos das outras ruas. O terminal informa o total encontrado e lista até 50 nomes.',
    'Use a lista para conferir conectividade e escolher nomes para novas buscas. Uma lista vazia pode indicar nome divergente, rua ausente ou falta de nós compartilhados no arquivo.',
    'Compartilhar um nó na base não garante que toda manobra seja permitida. Cruzamentos geométricos sem nó comum, como certas passagens em desnível ou falhas de segmentação, não são reconhecidos por este procedimento.'
  ],
  grafo: [
    'Permite inspecionar visualmente a extensão e a forma dos segmentos que compõem a malha viária carregada.',
    'Lê o CSV do grafo e desenha suas arestas a partir das coordenadas. A figura gerada pelo visualizador do terminal fica disponível nos resultados da interface.',
    'Procure lacunas, segmentos deslocados, ligações inesperadas ou regiões ausentes. A imagem ajuda a localizar possíveis problemas para uma análise posterior dos dados.',
    'Uma malha visualmente contínua não comprova conectividade entre todos os pares, sentido correto das vias ou qualidade das altitudes. Este cartão não executa essas verificações automaticamente.'
  ],
  colunas: [
    'Permite verificar se o shapefile de ruas pode ser lido e quais campos e registros iniciais ele oferece ao processamento.',
    'Carrega o arquivo do IPPUC com GeoPandas e exibe os nomes das colunas e as primeiras linhas no Terminal. É uma inspeção de entrada antes de gerar ou diagnosticar o grafo.',
    'Confira se os campos esperados estão presentes e se os exemplos de nomes e geometria fazem sentido. Falha de leitura pode indicar arquivo ausente, componentes do shapefile faltando ou dependência indisponível.',
    'Ler as primeiras linhas não valida todas as geometrias nem a qualidade da base inteira. Esta inspeção não produz rotas nem comprova consistência topológica.'
  ],
  nomes: [
    'Ajuda a diagnosticar a nomenclatura usada na seleção de ruas e a estrutura da base de origem.',
    'Conta nomes únicos no CSV do grafo, mostra uma amostra de até 20 nomes e inspeciona colunas e primeiras linhas do shapefile do IPPUC.',
    'Confira grafia, abreviações e acentos ao preencher origem e destino. Os campos do shapefile ajudam a identificar de onde os nomes utilizados no processamento são obtidos.',
    'O cartão exibe amostras e não faz uma conciliação completa entre todas as ruas das duas bases. Não encontrar um nome na amostra não significa que ele esteja ausente do grafo.'
  ],
  etl: [
    'Prepara os dados necessários ao roteamento, transformando os shapefiles do IPPUC em um CSV de grafo com segmentos e informações de relevo.',
    'Executa o processamento de ruas e curvas de nível e exporta o novo grafo para os resultados desta execução. A interface preserva o CSV de trabalho existente; a adoção do arquivo gerado é uma etapa separada.',
    'Consulte o Terminal para acompanhar a leitura e a geração e abra o CSV para inspecionar as colunas e valores. O arquivo exportado pode ser usado na raiz do projeto após a conferência da malha e de seus dados.',
    'Gerar o arquivo sem erro confirma o término do processamento, não a qualidade completa da topologia ou das altitudes. Rotas, conectividade e coerência física devem ser avaliadas nas operações correspondentes.'
  ]
};

function explicacaoDaOperacao(op) {
  return explicacoes[op.id] || [
    `Verifica as condições automatizadas definidas em ${op.arquivo || op.nome}.`,
    'Executa os casos disponíveis para esta operação. Cada asserção compara o comportamento observado com o esperado pelo código de teste.',
    'Consulte no Terminal os casos aprovados, as falhas e os testes ignorados. Uma execução sem falha só fornece evidência sobre os casos efetivamente executados.',
    'Este módulo foi descoberto automaticamente e ainda não possui um guia específico. Consulte suas asserções para conhecer os critérios exatos; não há uma conclusão científica adicional definida por este texto.'
  ];
}
