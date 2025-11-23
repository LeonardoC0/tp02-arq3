# Simulador do Algoritmo de Tomasulo com Interface Gráfica

## Introdução

Este projeto é um simulador didático do algoritmo de Tomasulo, uma técnica crucial na arquitetura de computadores para permitir a execução de instruções fora de ordem (Out-of-Order Execution) em processadores superescalares.

O simulador foi desenvolvido em **Python**, com uma interface gráfica interativa (Tkinter) que permite a visualização passo a passo do fluxo de instruções através dos componentes principais do pipeline:

* **Estações de Reserva (Reservation Stations - RS)**
* **Reorder Buffer (ROB)**
* **Arquivo de Registradores**

### Objetivo

O objetivo é auxiliar estudantes e entusiastas em arquitetura de computadores a compreenderem conceitos complexos como:

* ✅ **Renomeação de Registradores:** Eliminação de dependências *WAR* e *WAW*.
* ✅ **Comunicação via Common Data Bus (CDB):** Propagação rápida de resultados.
* ✅ **Execução Fora de Ordem:** Como as instruções podem ser executadas quando seus operandos estão prontos, independentemente da ordem do programa.
* ✅ **Confirmação em Ordem:** O papel do ROB em garantir que o estado arquitetônico seja atualizado sequencialmente.
* ✅ **Especulação de Desvio:** Como o pipeline lida com a previsão de *branches* e a recuperação de erros (*flushing*) em caso de erro na previsão.

O simulador utiliza um conjunto de instruções **MIPS-like** e apresenta métricas de desempenho como:

* 📊 **IPC (Instruções Por Ciclo)**
* 🐢 **Ciclos de bolha (stalls)**

---

## Como Compilar e Executar

### ✅ Pré-requisitos

* **Python 3.8 ou superior.**

### 🔧 Passos para Execução

1. **Salve o Código:**
   Salve o código Python do simulador em um arquivo chamado `tomasulo_simulator_gui.py` (ou outro nome de sua preferência).

2. **Verifique o Arquivo de Instruções (`instructions.txt`):**
   O simulador lê as instruções de um arquivo chamado `instructions.txt`, localizado no mesmo diretório do script Python.

   * Se não existir, o simulador cria um automaticamente com um exemplo padrão.
   * Você pode editar este arquivo com suas próprias instruções no seguinte formato:

   #### Formato das Instruções:

   * 📌 **Operações Aritméticas:**
     `OP Rd, Rs, Rt` → Ex.: `ADD R1, R2, R3`
   * 📌 **Shift:**
     `OP Rd, Rs, immediate` → Ex.: `SLLI R1, R2, 5`
   * 📌 **Load:**
     `OP Rdest, Rbase, offset` → Ex.: `LW R6, R12, 8`
   * 📌 **Store:**
     `OP Rsrc, Rbase, offset` → Ex.: `SW R18, R0, 16`
   * 📌 **Branch:**
     `OP Rs1, Rs2, target_address` → Ex.: `BEQ R6, R0, 10`

     * Onde `target_address` é o índice da instrução alvo, começando em 0.
   * ⚠️ Linhas começando com `#` são comentários e serão ignoradas.

3. **Execute o Simulador:**

   * Abra um terminal ou prompt de comando.
   * Navegue até o diretório onde você salvou o arquivo.
   * Execute:


   ```bash
   python tomasulo_simulator_gui.py
   ```

4. **Interaja com a Interface Gráfica:**
   Uma janela abrirá exibindo o estado inicial do simulador.

   #### ▶️ **Botões de Controle:**

   * **Próximo Ciclo:** Avança a simulação um ciclo de clock.
   * **Executar Tudo:** Executa até o fim com delay entre ciclos.
   * **Reiniciar:** Limpa o estado atual e reinicia a simulação.
   * **Carregar Programa:** Recarrega o arquivo `instructions.txt`.

   #### 🖥️ **Painéis de Visualização:**

   * **Programa de Instruções:** Exibe o código carregado com destaque no PC atual.
   * **Reorder Buffer (ROB):** Estado das entradas do ROB.
   * **Estações de Reserva (RS):** Estado das RS para cada unidade funcional.
   * **Arquivo de Registradores:** Mostra valores, tags e status dos registradores.
   * **Memória:** Visualização das primeiras posições da memória.
   * **Métricas de Desempenho:** Ciclos, IPC, instruções concluídas e stalls.

---

## 👥 Participantes do Projeto

- Caio Ronan Horta  
- Daniel Valadares
- Felipe Silva Faria  
- Thiago Cedro Silva de Souza 

---

## 📜 Licença

Projeto desenvolvido para fins didáticos no âmbito da disciplina de **Arquitetura de Computadores**, PUC Minas, 2025.
