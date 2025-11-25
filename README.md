# TP02 – Simulador do Algoritmo de Tomasulo com ROB e Predição de Desvio

Este projeto implementa um simulador ciclo-a-ciclo de um processador MIPS-like com pipeline dinâmico, seguindo o **Algoritmo de Tomasulo**. O objetivo é demonstrar visualmente o funcionamento da execução fora de ordem (Out-of-Order) e especulativa.

O simulador inclui:
* **Estações de Reserva (Reservation Stations)**
* **Renomeação de registradores**
* **Common Data Bus (CDB)**
* **Execução fora de ordem (OoO)**
* **Buffer de Reordenação (ROB)**
* **Predição estática de desvio (Always Not Taken)**
* **Interface Gráfica (GUI)** desenvolvida com `tkinter`.

A interface permite carregar traces de instruções, executar o código passo a passo (ou ciclo a ciclo) e visualizar o estado interno de todos os componentes do pipeline.

## Autores

* Leonardo Carvalho

* Lucas Cabral

* Pedro Gaioso

* Thiago Cedro

---

## 1. Requisitos

* **Python 3.8+**
* Bibliotecas padrão (não é necessário instalar pacotes externos):
    * `tkinter` (interface gráfica)
    * `collections`
    * `copy`
    * `os`

---

## 2. Arquivos do Projeto

A estrutura do diretório deve estar organizada da seguinte forma:

```
.
├── tomasulo_sim.py          # Código principal do simulador e interface
├── trace_sem_desvio.txt     # Exemplo de trace linear
├── trace_com_desvio.txt     # Exemplo de trace com branch (BEQ/BNE)
└── README.md                # Documentação do projeto
```

## 3. Como Rodar

### Passo 1 — Clonar o repositório
```
git clone [https://github.com/LeonardoC0/tp02-arq3.git]

cd tp02-arq3
```

### Passo 2 — Executar o simulador
```
python tomasulo_sim.py
```
Nota: A janela da interface gráfica Tkinter será aberta imediatamente após a execução do comando.
## 4. Como Usar a Interface
1) Carregar um trace
* Clique no botão "Carregar Trace".
* Selecione um arquivo .txt contendo instruções no formato MIPS-like.
Exemplo de formato aceito:
ADD R1, R2, R3
SUB R4, R1, R5
LW R6, 0(R1)
BEQ R1, R2, LABEL
2) Executar a simulação
* "Próximo Ciclo": avança uma etapa completa do pipeline
* "Executar Tudo": roda até o final
* As tabelas exibem:
  * Estações de reserva
  * ROB
  * Estados dos registradores. Fu
  * Pipeline (Issue / Execute / Write / Commit)
  * Informações de predição de desvio
