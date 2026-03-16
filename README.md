# Escopo do Projeto: Análise, Projeto e Complexidade de Algoritmos para Otimização de Rotas Multimodais no Recife

**Foco:** Deslocamento estratégico entre o Cine São Luiz (Centro) e a Faculdade Nova Roma (Boa Viagem).

**Equipe:** João Lucas Camilo Ramos, Diego Henrique Moreira Galvão, Ana Beatriz Vieira de Melo, Adauto Paes e Juliano Freitas.

## 1. Introdução

A mobilidade urbana representa um dos desafios estruturais mais críticos das metrópoles contemporâneas. No contexto da cidade do Recife, essa problemática é acentuada por uma malha viária saturada, frequentemente posicionando a capital pernambucana entre as cidades mais congestionadas do mundo. O deslocamento entre polos estratégicos, como o Cine São Luiz (Rua da Aurora) e a Faculdade Nova Roma (Boa Viagem), serve como cenário ideal para observar como a ineficiência no planejamento de rotas impacta diretamente o tempo e a qualidade de vida do cidadão.

Para enfrentar essa complexidade, este projeto propõe o desenvolvimento e a análise de algoritmos voltados à otimização de rotas multimodais. Diferente das soluções de navegação convencionais, a abordagem multimodal integra diversos meios de transporte: ônibus, metrô, BRT, transporte por aplicativo, bicicleta e caminhada, em um único modelo computacional.

O foco central deste estudo reside na Análise e Projeto de Algoritmos, onde serão exploradas técnicas de busca em grafos, como os algoritmos de Dijkstra e A*, adaptados para lidar com pesos dinâmicos. Esses pesos representarão variáveis reais como o tráfego em horários de pico, custos tarifários, condições climáticas e o impacto ambiental.

Além da implementação prática, o projeto dedica-se à investigação da complexidade computacional dessas soluções, avaliando a viabilidade técnica e a eficiência dos algoritmos em processar grandes volumes de dados da rede de transporte do Recife. Ao final, busca-se não apenas encontrar o "caminho mais curto", mas a rota que melhor equilibre os múltiplos objetivos de custo, tempo e sustentabilidade para o usuário urbano.

## 2. Requisitos

O levantamento de requisitos para o "Sistema de Análise e Otimização de Rotas em Redes Urbanas" deve se concentrar em identificar as funcionalidades essenciais e as restrições de desempenho, usabilidade e integração de dados dinâmicos.

### 2.1 Requisitos Funcionais

1. **Modelagem da Malha Urbana via Grafos:** O sistema deve representar a rede urbana (vias e cruzamentos) através de uma estrutura de grafo direcionado, onde os cruzamentos são tratados como vértices e os segmentos de via (ruas e avenidas) como arestas ponderadas. O sistema deve permitir a importação de dados geográficos e a inclusão de pontos de interesse específicos (ex: Cine São Luiz).

2. **Cálculo de Rotas Multi-objetivo:** O sistema deve calcular a trajetória entre um ponto de origem e um ou mais destinos utilizando algoritmos de busca (como A* ou Dijkstra), permitindo ao usuário selecionar a prioridade do cálculo:
   - a. Eficiência Temporal: Foco no menor tempo de deslocamento.
   - b. Eficiência Espacial: Foco na menor distância física.
   - c. Economia de Recursos: Foco no menor consumo de combustível.
   - d. Segurança: Priorização de vias com melhores índices de segurança reportados.

3. **Processamento de Variáveis Dinâmicas e Ambientais:** O sistema deve ajustar os pesos das arestas do grafo em tempo real, aplicando coeficientes de correção baseados em:
   - a. Condições Climáticas: Impacto da chuva na velocidade média e segurança das vias.
   - b. Eventos e Sazonalidade: Alterações no fluxo devido a jogos de futebol, feriados ou épocas festivas.
   - c. Restrições de Tráfego: Sentido das vias, sinistros (acidentes), protestos e bloqueios temporários.

4. **Análise Preditiva de Fluxo:** O sistema deve modelar e prever a fluidez do trânsito com base em séries históricas e dados em tempo real, diferenciando o comportamento do tráfego por horários de pico e segmentos específicos da via.

5. **Comparação Multimodal de Trajetos:** O sistema deve permitir a comparação simultânea de tempo e custo entre diferentes modos de transporte (carro, moto, transporte público e pedestre).

6. **Re-Cálculo Dinâmico de Rota:** O sistema deve monitorar a posição do usuário durante o trajeto e disparar automaticamente um novo cálculo de rota caso uma restrição dinâmica (ex: novo bloqueio na via) torne o caminho atual inviável ou significativamente mais lento.

7. **Interface de Visualização Cartográfica:** O sistema deve renderizar a rota otimizada e as alternativas sobre um mapa digital, destacando visualmente trechos de lentidão, incidentes e a estimativa de custo/tempo para cada modal comparado.

## 3. Objetivos

### 3.1. Objetivo Geral

Desenvolver e analisar algoritmos para a otimização de rotas multimodais integrando ônibus, metrô, BRT, transporte por aplicativo, bicicleta e caminhada.

### 3.2. Objetivos Específicos

- Modelar a rede de transporte do Recife como um grafo multimodal (onde nós são paradas/interconexões e arestas são tempos/custos de deslocamento).
- Implementar e comparar algoritmos clássicos (Dijkstra e A*) adaptados para custos variáveis.
- Desenvolver um algoritmo de otimização multiobjetivo (Equilíbrio entre tempo, custo e impacto ambiental).
- Analisar a complexidade computacional e o desempenho dos algoritmos em cenários de pico e fora de pico.

## 4. Metodologia

O projeto será desenvolvido em quatro etapas principais:

### 1. Revisão da Literatura e Coleta de Dados

A transição entre a fundamentação teórica e a implementação prática baseia-se na conversão de dados urbanos em uma estrutura de Grafo Multimodal Dinâmico. Esta etapa sistematiza como as fontes de dados do Recife alimentam os requisitos dos algoritmos de Dijkstra e A*.

- **Abstração da Malha Urbana (Vértices e Arestas):** Conforme discutido na revisão sobre Grafos, a rede viária do Recife será mapeada utilizando o OpenStreetMap (OSM).
  - **Vértices (V):** Representarão cruzamentos, paradas de ônibus do Grande Recife Consórcio, estações de metrô e pontos de transbordo entre modais.
  - **Arestas (E):** Representarão os segmentos de via e as linhas de transporte público. Para a conexão entre o Cine São Luiz e a Faculdade Nova Roma, as arestas incluirão atributos de distância física e velocidade média permitida pela CTTU.
- **Definição de Pesos e Custos Variáveis:** Para que o Algoritmo de Dijkstra e o A* operem além da distância geométrica, a coleta de dados fornecerá os pesos (w) das arestas:
  - **Custo Temporal:** Dados históricos do TomTom Traffic Index e boletins de tempo real da CTTU permitirão calcular o tempo de deslocamento variando conforme o horário (pico vs. vale).
  - **Custo Tarifário:** O valor das passagens (Anéis A, B, G) fornecido pelo Grande Recife será integrado como um peso de custo financeiro, essencial para o requisito de "Economia de Recursos".

A base empírica para a construção do grafo multimodal e a calibração dos pesos das arestas será obtida por meio de um processo de triangulação de dados, utilizando fontes governamentais oficiais e plataformas de mapeamento colaborativo e comercial:

- **OpenStreetMap:** É uma ferramenta de mapeamento mundial colaborativa, surgiu no ano de 2004, pelo estudante de computação Steve Coast, da University College London (UCL).
- **Infraestrutura e Malha Viária (Dados Estáticos):** A geometria das vias, sentidos de tráfego e restrições de manobra serão extraídos do OpenStreetMap (OSM) via API Overpass. Esses dados fornecem a topologia necessária para a criação do grafo base (vértices e arestas).
- **Sistema de Transporte Público (Dados Semi Estáticos):** Informações sobre itinerários, localização de paradas e quadros de horários do sistema de ônibus e BRT serão obtidas através do Grande Recife Consórcio de Transporte. Utilizaremos arquivos no padrão GTFS (General Transit Feed Specification), que permitem integrar as linhas de transporte público à rede de caminhada do OSM, viabilizando a multimodalidade.
- **Trânsito e Gestão Urbana (Dados Dinâmicos):** Para a modelagem de pesos variáveis (congestionamentos e incidentes), serão consultados os boletins informativos da CTTU (Autarquia de Trânsito e Transporte Urbano do Recife). Complementarmente, serão coletadas estimativas de tempo de percurso em horários de pico e fora de pico através da API do Google Maps ou TomTom Traffic Stats, permitindo que o algoritmo de "Dijkstra/A*" considere o "custo tempo" real do deslocamento entre o Centro e Boa Viagem.

**CARRO**

| ROTA | PERCURSO | TEMPO |
|------|----------|-------|
| 1 | PE-009 | 18min |
| 2 | Av Domingos Ferreira | 18min |
| 3 | Rua Imperial e Av Domingos Ferreira | 18min |

**MOTO**

| ROTA | PERCURSO | TEMPO |
|------|----------|-------|
| 1 | PE-009 | 15min |
| 2 | Av Domingos Ferreira | 15min |
| 3 | Rua Imperial e Av Domingos Ferreira | 15min |

**CAMINHADA**

| ROTA | PERCURSO | TEMPO |
|------|----------|-------|
| 1 | Av Domingos Ferreira | 2h |
| 2 | Rua Imperial | 2h,1min |

**ÔNIBUS**

| ROTA | PERCURSO | TEMPO |
|------|----------|-------|
| 1 | Setúbal (Príncipe) | 34min |
| 2 | Catamarã | 35min |
| 3 | TI Recife/TI Joana Bezerra | 38min |
| 4 | Candeias | 41min |

**BICICLETA**

| ROTA | PERCURSO | TEMPO |
|------|----------|-------|
| 1 | Via Mangue | 34min |
| 2 | Av. Boa Viagem | 33min |
| 3 | Rua Arquiteto Luiz Nunes | 39min |

### 2. Modelagem e Implementação dos Algoritmos

Esta etapa consiste na construção do "motor" do projeto, transformando as informações geográficas e logísticas em um modelo computacional capaz de realizar inferências de rota.

#### 2.1. Modelagem do Grafo Multimodal de Recife

A rede de transporte será modelada como um Grafo Direcionado Ponderado G = (V, E), onde a multimodalidade é introduzida através de camadas de interconexão:

- **Vértices (V):** Representarão pontos críticos de decisão, como cruzamentos viários, paradas de ônibus (dados GTFS do Grande Recife), estações de metrô e o terminal de passageiros. O Cine São Luiz e a Faculdade Nova Roma foram definidos como nós de origem (s) e destino (t), respectivamente.
- **Arestas (E):** Segmentadas por modalidade. As arestas de "caminhada" conectam o usuário aos pontos de transporte público, enquanto as arestas de "transporte" representarão o deslocamento físico entre paradas ou interseções.
- **Função de Custo (Pesos):** Cada aresta e E receberá um vetor de pesos W(e) = {t, c, s}, onde:
  - t = tempo de percurso (ajustado por fatores de tráfego da CTTU);
  - c = custo financeiro (tarifas vigentes);
  - s = fator de sustentabilidade/segurança.

#### 2.2. Implementação Computacional em Python

A implementação será realizada em Python, utilizando bibliotecas especializadas para manipulação de redes complexas e dados geoespaciais:

- **NetworkX / OSMnx:** Para a criação e manipulação da estrutura do grafo e importação da malha urbana do OpenStreetMap.
- **Pandas / Geopandas:** Para o tratamento das tabelas de horários do Grande Recife e coordenadas geográficas.

#### 2.3. Desenvolvimento dos Algoritmos de Busca

Serão implementadas e adaptadas três abordagens principais:

- **Algoritmo de Dijkstra:** Utilizado como baseline para garantir a descoberta do caminho mínimo absoluto em termos de custo acumulado, explorando a fronteira de nós de forma radial.
- **Algoritmo A*:** Implementado para otimizar o tempo de processamento. A função de busca será definida por f(n) = g(n) + h(n), onde a heurística h(n) será a distância de Haversine (levando em conta a curvatura da Terra) entre o nó atual e a Faculdade Nova Roma, acelerando a convergência no eixo Centro-Boa Viagem.
- **Otimização Multiobjetivo:** Desenvolvimento de um algoritmo de Fronteira de Pareto, que não entrega apenas uma rota, mas um conjunto de soluções ótimas (ex: a rota mais rápida vs. a rota mais barata via transporte público).

#### 2.4. Tratamento de Variáveis Dinâmicas

Diferente de grafos estáticos, a implementação prevê a reponderação de arestas. Caso os dados da CTTU indiquem um bloqueio na Avenida Agamenon Magalhães, o peso "t" das arestas afetadas será elevado ao infinito, forçando os algoritmos a recalcular o desvio em tempo real.

### 3. Simulação e Análise de Resultados

- Realização de simulações para avaliar o desempenho dos algoritmos em diferentes cenários, considerando variações de horário, dia da semana e condições de tráfego.
- Análise comparativa dos resultados obtidos pelos diferentes algoritmos, considerando os critérios de otimização definidos.

### 4. Elaboração do Relatório Final e Proposta de Sistema

- Elaboração de um relatório técnico detalhando a metodologia, os resultados e as conclusões do projeto.
- Proposta de uma arquitetura de sistema para uma aplicação de recomendação de rotas multimodais, incluindo a descrição dos componentes e das tecnologias a serem utilizadas.

## 5. Cronograma

| ETAPA | Fev | Mar | Abr | Mai | Jun |
|-------|:---:|:---:|:---:|:---:|:---:|
| Revisão da Literatura e Coleta de Dados | X | X | | | |
| Modelagem e Implementação dos Algoritmos | | | X | X | |
| Simulação e Análise de Resultados | | | | X | X |
| Elaboração do Relatório Final e Proposta | | | | | X |

## 6. Referências

[1] TomTom Traffic Index. (2023). Recife Traffic. Disponível em: https://www.tomtom.com/traffic-index/recife-traffic/

[2] Bast, H., Delling, D., Goldberg, A., Müller-Hannemann, M., Pajor, T., Sanders, P., … & Werneck, R. F. (2016). Route planning in transportation networks. In Algorithm engineering (pp. 19-80). Springer, Cham.

[3] Liu, L., Mu, H., & Yang, J. (2017). Toward algorithms for multi-modal shortest path problem and their extension in urban transit network. Journal of Intelligent Manufacturing, 28(5), 1143-1154.

[4] Yusuf, O., Rasheed, A., & Lindseth, F. (2025). Leveraging Big Data and AI for Sustainable Urban Mobility Solutions. Urban Science, 9(8), 301.

[5] Jain, Y., & Pandey, K. (2025). Transforming Urban Mobility: A Systematic Review of AI-Based Traffic Optimization Techniques. Archives of Computational Methods in Engineering.

[6] Tu, Q., Cheng, L., Yuan, T., Cheng, Y., & Li, M. (2020). The constrained reliable shortest path problem for electric vehicles in the urban transportation network. Journal of Cleaner Production, 257, 120531.

[7] Sharieh, A. (2024). Modeling Metaheuristic Algorithms to Optimal Pathfinding for Vehicles. WSEAS Transactions on Computers, 23, a605105-029.

[8] Deng, X., Chang, L., Zeng, S., Cai, L., & Poor, H. V. (2022). Distance-based back pressure routing for load-balancing LEO satellite networks. IEEE Transactions on Wireless Communications, 21(11), 9679-9692.

[9] Gendreau, M., Ghiani, G., & Guerriero, E. (2015). Time-dependent routing problems: A review. Computers & Operations Research, 64, 189-200.

[10] Fang, Z., Li, L., Li, B., Zhu, J., & Li, Q. (2017). An artificial bee colony-based multi-objective route planning algorithm for use in pedestrian navigation at night. International Journal of Geographical Information Science, 31(11), 2249-2270.

[11] Abbatecola, L., Fanti, M. P., and Ukovich, W. (2016). A review of new approaches for dynamic vehicle routing problem. In 12th Conference on Automation Science and Engineering.

[12] Hà, M. H., Bostel, N., Langevin, A., and Rousseau, L. (2014). An exact algorithm and a metaheuristic for the generalized vehicle routing problem with flexible fleet size. Computers & Operations Research, 43:9–19.

[13] Kuo, R. J. and Zulvia, F. E. (2017). Hybrid genetic ant colony optimization algorithm for capacitated vehicle routing problem with fuzzy demand - a case study on garbage collection system. In 4th International Conference on Industrial Engineering and Applications (ICIEA), page 244–248.

[14] Barroso, Maria. (2014). Aplicações de grafo em um problema de rede. Disponível em: https://periodicos.pucminas.br/abakos/article/download/P.2316-9451.2014v2n2p48/6406/27281

[15] Atzingen, J., Cunha, C., Nakamoto, F., Ribeiro, F., & Schardong, A. (2012). Análise comparativa de algoritmos eficientes para o problema de caminho mínimo. Disponível em: https://www.researchgate.net/profile/Andre-Schardong/publication/267846283_ANALISE_COMPARATIVA_DE_ALGORITMOS_EFICIENTES_PARA_O_PROBLEMA_DE_CAMINHO_MINIMO/links/54b8fdf10cf28faced62656d/ANALISE-COMPARATIVA-DE-ALGORITMOS-EFICIENTES-PARA-O-PROBLEMA-DE-CAMINHO-MINIMO.pdf

[15] Medeiros, Gabriel. (2012). OpenStreetMap: Uma análise sobre a evolução de dados geográficos colaborativos no Brasil. Disponível em: https://bdm.unb.br/bitstream/10483/19524/1/2017_GabrielFranklinBrazdeMedeiros.pdf
