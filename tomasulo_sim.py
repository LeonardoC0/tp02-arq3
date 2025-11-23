import collections
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import copy  # Import necessário para salvar o estado

# Constantes globais para estados e tipos de branch
JUMP = "JUMP"
PREDICT_NOT_TAKEN = "NOT_TAKEN"
PREDICT_TAKEN = "TAKEN"

# --- Classe Instruction ---
class Instruction:
    def __init__(self, op, rs1, rs2=None, rd=None, shamt=None, imn=None):
        self.opname = op
        self.destination = rd
        self.source1 = rs1
        self.source2 = rs2
        self.immediate = shamt
        self.address = imn
        
        # Atributos de estado do pipeline
        self.execution_cycles_remaining = self._get_execution_cycles(op)
        self.ready_to_write = False
        self.issue_cycle = -1
        self.execute_start_cycle = -1
        self.write_result_cycle = -1
        self.commit_cycle = -1
        self.state_at_cycle = {}

    def _get_execution_cycles(self, opname):
        if opname in ['ADD', 'SUB']: return 2
        elif opname in ['SLLI', 'SRLI', 'OR', 'AND', 'BEQ', 'BNE']: return 1
        elif opname in ['LW', 'LB', 'SW', 'SB']: return 5
        elif opname in ['MUL', 'DIV']: return 3
        else: return 1

    # Reseta os atributos de estado do pipeline para re-execução
    def reset_pipeline_state(self):
        self.execution_cycles_remaining = self._get_execution_cycles(self.opname)
        self.ready_to_write = False
        self.issue_cycle = -1
        self.execute_start_cycle = -1
        self.write_result_cycle = -1
        self.commit_cycle = -1
        self.state_at_cycle = {}

    def __str__(self):
        if self.opname in ['SLLI', 'SRLI']:
            return f'{self.opname} {self.destination}, {self.source1}, {self.immediate}'
        elif self.opname in ['LW', 'LB']:
            return f'{self.opname} {self.destination}, {self.source1}, {self.address}'
        elif self.opname in ['SW', 'SB']:
            return f'{self.opname} {self.source2}, {self.source1}, {self.address}'
        elif self.opname in ['BEQ', 'BNE']:
            return f'{self.opname} {self.source1}, {self.source2}, {self.address}'
        elif self.opname in ['MUL', 'DIV', 'ADD', 'SUB', 'OR', 'AND']:
            return f'{self.opname} {self.destination}, {self.source1}, {self.source2}'
        else:
            return f'{self.opname} {self.destination}, {self.source1}, {self.source2}'


# --- Classe Register ---
class Register:
    def __init__(self, name):
        self.name = name
        self.value = 0
        self.reorder_tag = None
        self.busy = False

    def clear(self):
        self.reorder_tag = None
        self.busy = False

    def __str__(self):
        return f'{self.name}: Val={self.value}, ROB={self.reorder_tag}, Busy={self.busy}'

# --- Classe ReorderBufferPos ---
class ReorderBufferPos:
    def __init__(self, id, instruction, destination_reg, inst_type):
        self.id = id
        self.busy = False
        self.instruction = instruction
        self.state = ""
        self.destination_reg = destination_reg
        self.value = None
        
        self.inst_type = inst_type
        self.is_branch = (inst_type == "BRANCH")
        self.predicted_taken = None
        self.actual_taken = None
        self.target_address = None
        self.program_order_index = -1
        self.source_rs = None

    def clear(self):
        self.busy = False
        if self.instruction:
            self.instruction.reset_pipeline_state()
        self.instruction = None
        self.state = ""
        self.destination_reg = ""
        self.value = None
        self.inst_type = ""
        self.is_branch = False
        self.predicted_taken = None
        self.actual_taken = None
        self.target_address = None
        self.program_order_index = -1
        self.source_rs = None

    def __str__(self):
        return (f'#{self.id} Busy:{self.busy} Inst:{self.instruction} State:{self.state} '
                f'Dest:{self.destination_reg} Val:{self.value} Type:{self.inst_type}')

# --- Classe ReservationStation ---
class ReservationStation:
    def __init__(self, name):
        self.name = name
        self.busy = False
        self.op = None
        self.Vj = None
        self.Vk = None
        self.Qj = None
        self.Qk = None
        self.destination_rob_id = None
        self.instruction_obj = None

    def clear(self):
        self.busy = False
        self.op = None
        self.Vj = None
        self.Vk = None
        self.Qj = None
        self.Qk = None
        self.destination_rob_id = None
        self.instruction_obj = None

    def is_clear(self):
        return not self.busy

    def __str__(self):
        return (f'Name:{self.name} Busy:{self.busy} Op:{self.op} Vj:{self.Vj} Vk:{self.Vk} '
                f'Qj:{self.Qj} Qk:{self.Qk} Dest_ROB:{self.destination_rob_id}')

# --- Classe TomasuloSimulator ---
class TomasuloSimulator:
    def __init__(self, num_mem_rs=2, num_add_rs=3, num_logic_rs=2, num_mult_rs=1, rob_size=8):
        self.register_file = {}
        self.memory = collections.defaultdict(int)
        self.program_counter = 0
        self.program_length = 0

        self.reservation_stations = []
        self._create_reservation_stations(num_mem_rs, num_add_rs, num_logic_rs, num_mult_rs)

        self.reorder_buffer = [ReorderBufferPos(i, None, None, None) for i in range(rob_size)]
        self.rob_head = 0
        self.rob_tail = 0
        self.current_rob_entries = 0

        self.current_cycle = 0
        self.committed_instructions_count = 0
        self.bubble_cycles = 0

        self.is_running = False
        self.program_instructions = []
        
        # Pilha para armazenar o histórico de estados (Snapshots)
        self.history = []

    def _create_reservation_stations(self, num_mem, num_add, num_logic, num_mult):
        for i in range(num_mem):
            self.reservation_stations.append(ReservationStation(f"MEM{i+1}"))
        for i in range(num_add):
            self.reservation_stations.append(ReservationStation(f"ADD{i+1}"))
        for i in range(num_logic):
            self.reservation_stations.append(ReservationStation(f"BRANCH{i+1}")) 
        for i in range(num_mult):
            self.reservation_stations.append(ReservationStation(f"MUL{i+1}")) 

    def load_instructions(self, filename="teste.txt"):
        self.program_instructions.clear()
        self.register_file.clear()
        self.memory = collections.defaultdict(int)
        self.program_length = 0
        self.history.clear() # Limpa histórico ao carregar novo programa

        try:
            with open(filename, 'r') as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    tokens = [t.strip(',') for t in line.split()]
                    opname = tokens[0]

                    instruction = None
                    destination = None
                    source1 = None
                    source2 = None
                    immediate = None
                    address = None
                    inst_type = "ALU"

                    if opname in ['SLLI', 'SRLI']:
                        destination = tokens[1]
                        source1 = tokens[2]
                        immediate = int(tokens[3])
                    elif opname in ['LW', 'LB']: 
                        destination = tokens[1]
                        source1 = tokens[2]
                        address = int(tokens[3])
                        inst_type = "LOAD"
                    elif opname in ['SW', 'SB']: 
                        source2 = tokens[1]
                        source1 = tokens[2]
                        address = int(tokens[3])
                        inst_type = "STORE"
                    elif opname in ['BEQ', 'BNE']: 
                        source1 = tokens[1]
                        source2 = tokens[2]
                        address = int(tokens[3])
                        inst_type = "BRANCH"
                    elif opname in ['ADD', 'SUB', 'OR', 'AND', 'MUL', 'DIV']:
                        destination = tokens[1]
                        source1 = tokens[2]
                        source2 = tokens[3]
                        inst_type = "ALU"
                    else:
                        print(f"Warning: Instrução '{opname}' não reconhecida na linha: {line}. Ignorando.")
                        continue

                    instruction = Instruction(opname, source1, source2, destination, immediate, address)
                    self.program_instructions.append(instruction)

                    regs_to_check = []
                    if destination: regs_to_check.append(destination)
                    if source1: regs_to_check.append(source1)
                    if source2: regs_to_check.append(source2)

                    for reg_name in regs_to_check:
                        if reg_name and reg_name not in self.register_file:
                            self.register_file[reg_name] = Register(reg_name)
            self.program_length = len(self.program_instructions)
        except FileNotFoundError:
            messagebox.showerror("Erro de Carregamento", f"O arquivo de instruções '{filename}' não foi encontrado.")
            return False
        return True

    def _get_free_rob_entry(self):
        if self.reorder_buffer[self.rob_tail].busy:
            return -1 
        return self.rob_tail 

    def _get_free_rs(self, inst_opname):
        for rs in self.reservation_stations:
            if rs.is_clear():
                if inst_opname in ['LW', 'LB', 'SW', 'SB'] and rs.name.startswith("MEM"):
                    return rs
                elif inst_opname in ['ADD', 'SUB'] and rs.name.startswith("ADD"): 
                    return rs
                elif inst_opname in ['SLLI', 'SRLI', 'OR', 'AND', 'BEQ', 'BNE'] and rs.name.startswith("BRANCH"): 
                    return rs
                elif inst_opname in ['MUL', 'DIV'] and rs.name.startswith("MUL"): 
                    return rs
        return None

    # --- Estágio de Emissão (Issue) ---
    def issue_stage(self):
        issued_this_cycle = False
        if self.program_counter < self.program_length:
            inst_to_issue = self.program_instructions[self.program_counter]
            
            rob_id = self._get_free_rob_entry()
            rs_entry = self._get_free_rs(inst_to_issue.opname)

            if rob_id != -1 and rs_entry is not None:
                rob_pos = self.reorder_buffer[rob_id]
                rob_pos.busy = True 
                rob_pos.instruction = inst_to_issue
                rob_pos.state = "Issued"
                rob_pos.program_order_index = self.program_counter
                rob_pos.source_rs = rs_entry 

                if inst_to_issue.destination:
                    rob_pos.destination_reg = inst_to_issue.destination
                elif inst_to_issue.opname in ['SW', 'SB']:
                    base_reg_val = self.register_file[inst_to_issue.source1].value if inst_to_issue.source1 in self.register_file else 0
                    rob_pos.destination_reg = f"Mem[{inst_to_issue.address} + {inst_to_issue.source1} (Val:{base_reg_val})]"
                else:
                    rob_pos.destination_reg = None

                rob_pos.target_address = inst_to_issue.address

                if inst_to_issue.opname in ['ADD', 'SUB', 'SLLI', 'SRLI', 'OR', 'AND', 'MUL', 'DIV']:
                    rob_pos.inst_type = "ALU"
                elif inst_to_issue.opname in ['LW', 'LB']:
                    rob_pos.inst_type = "LOAD"
                elif inst_to_issue.opname in ['SW', 'SB']:
                    rob_pos.inst_type = "STORE"
                elif inst_to_issue.opname in ['BEQ', 'BNE']:
                    rob_pos.inst_type = "BRANCH"
                    rob_pos.predicted_taken = PREDICT_NOT_TAKEN 
                else:
                    rob_pos.inst_type = "UNKNOWN"

                inst_to_issue.issue_cycle = self.current_cycle

                rs_entry.busy = True
                rs_entry.op = inst_to_issue.opname
                rs_entry.destination_rob_id = rob_id
                rs_entry.instruction_obj = inst_to_issue

                if inst_to_issue.source1:
                    reg1 = self.register_file[inst_to_issue.source1]
                    if reg1.busy and reg1.reorder_tag is not None:
                        rob_entry_src1 = self.reorder_buffer[reg1.reorder_tag]
                        if rob_entry_src1.state == "Write Result" and rob_entry_src1.value is not None:
                            rs_entry.Vj = rob_entry_src1.value 
                        else:
                            rs_entry.Qj = reg1.reorder_tag
                    else:
                        rs_entry.Vj = reg1.value
                
                if inst_to_issue.opname in ['SLLI', 'SRLI']:
                    rs_entry.Vk = inst_to_issue.immediate
                elif inst_to_issue.opname in ['SW', 'SB']:
                    if inst_to_issue.source2:
                        reg2 = self.register_file[inst_to_issue.source2]
                        if reg2.busy and reg2.reorder_tag is not None:
                            rob_entry_src2 = self.reorder_buffer[reg2.reorder_tag]
                            if rob_entry_src2.state == "Write Result" and rob_entry_src2.value is not None:
                                rs_entry.Vk = rob_entry_src2.value
                            else:
                                rs_entry.Qk = reg2.reorder_tag
                        else:
                            rs_entry.Vk = reg2.value
                elif inst_to_issue.source2:
                    reg2 = self.register_file[inst_to_issue.source2]
                    if reg2.busy and reg2.reorder_tag is not None:
                        rob_entry_src2 = self.reorder_buffer[reg2.reorder_tag]
                        if rob_entry_src2.state == "Write Result" and rob_entry_src2.value is not None:
                            rs_entry.Vk = rob_entry_src2.value
                        else:
                            rs_entry.Qk = reg2.reorder_tag
                    else:
                        rs_entry.Vk = reg2.value

                if inst_to_issue.destination and inst_to_issue.opname not in ['SW', 'SB', 'BEQ', 'BNE']:
                    dest_reg = self.register_file[inst_to_issue.destination]
                    dest_reg.busy = True
                    dest_reg.reorder_tag = rob_id

                self.program_counter += 1
                self.rob_tail = (self.rob_tail + 1) % len(self.reorder_buffer)
                self.current_rob_entries += 1
                issued_this_cycle = True
        return issued_this_cycle

    # --- Estágio de Execução (Execute) ---
    def execute_stage(self):
        units_executing_this_cycle = {
            "ADD": False, "MUL": False, "BRANCH": False, "MEM": False
        }

        rs_to_process = []
        for rs in self.reservation_stations:
            if rs.busy:
                rob_entry_id = rs.destination_rob_id
                if rob_entry_id is None or not self.reorder_buffer[rob_entry_id].busy:
                    rs.clear() 
                    continue 
                rs_to_process.append(rs)

        ready_to_start_exec = []
        already_executing = []

        for rs in rs_to_process:
            inst_obj = rs.instruction_obj
            if inst_obj.execute_start_cycle == -1:
                if rs.Qj is None and rs.Qk is None:
                    ready_to_start_exec.append(rs)
            else:
                already_executing.append(rs)

        for rs in already_executing:
            inst_obj = rs.instruction_obj
            rob_entry = self.reorder_buffer[rs.destination_rob_id] 

            inst_obj.execution_cycles_remaining -= 1

            if inst_obj.execution_cycles_remaining == 0:
                inst_obj.ready_to_write = True
                rob_entry.state = "Ready to Write"

                result = None
                if inst_obj.opname in ['ADD', 'SUB', 'OR', 'AND']:
                    val1 = rs.Vj if rs.Vj is not None else 0
                    val2 = rs.Vk if rs.Vk is not None else 0
                    if inst_obj.opname == 'ADD': result = val1 + val2
                    elif inst_obj.opname == 'SUB': result = val1 - val2
                    elif inst_obj.opname == 'OR': result = val1 | val2
                    elif inst_obj.opname == 'AND': result = val1 & val2
                elif inst_obj.opname in ['MUL', 'DIV']:
                    val1 = rs.Vj if rs.Vj is not None else 0
                    val2 = rs.Vk if rs.Vk is not None else 0
                    if inst_obj.opname == 'MUL': result = val1 * val2
                    elif inst_obj.opname == 'DIV': 
                        if val2 != 0: result = val1 // val2
                        else: result = "DIV_BY_ZERO_ERROR"
                elif inst_obj.opname in ['SLLI', 'SRLI']:
                    val = rs.Vj if rs.Vj is not None else 0
                    shift_amount = rs.Vk if rs.Vk is not None else 0 
                    if inst_obj.opname == 'SLLI': result = val << shift_amount
                    elif inst_obj.opname == 'SRLI': result = val >> shift_amount
                elif inst_obj.opname in ['LW', 'LB']:
                    base_val = rs.Vj if rs.Vj is not None else 0
                    offset = inst_obj.address
                    effective_address = base_val + offset
                    result = self.memory[effective_address]
                elif inst_obj.opname in ['SW', 'SB']:
                    base_reg_value = rs.Vj 
                    value_to_be_stored = rs.Vk 
                    offset = inst_obj.address 
                    effective_address = base_reg_value + offset
                    self.memory[effective_address] = value_to_be_stored
                    result = "MEM_STORED"
                elif inst_obj.opname in ['BEQ', 'BNE']:
                    val1 = rs.Vj if rs.Vj is not None else 0
                    val2 = rs.Vk if rs.Vk is not None else 0
                    condition_met = (val1 == val2 if inst_obj.opname == 'BEQ' else val1 != val2)
                    rob_entry.actual_taken = PREDICT_TAKEN if condition_met else PREDICT_NOT_TAKEN
                    result = "BRANCH_EVALUATED"
                
                rob_entry.value = result
        
        ready_to_start_exec.sort(key=lambda x: x.destination_rob_id)

        for rs in ready_to_start_exec:
            inst_obj = rs.instruction_obj
            rob_entry = self.reorder_buffer[rs.destination_rob_id]
            
            unit_type = None
            if rs.name.startswith("ADD"): unit_type = "ADD"
            elif rs.name.startswith("MUL"): unit_type = "MUL"
            elif rs.name.startswith("BRANCH"): unit_type = "BRANCH"
            elif rs.name.startswith("MEM"): unit_type = "MEM"

            if unit_type and not units_executing_this_cycle[unit_type]:
                units_executing_this_cycle[unit_type] = True

                inst_obj.execute_start_cycle = self.current_cycle
                rob_entry.state = "Executing"
                
                inst_obj.execution_cycles_remaining -= 1

                if inst_obj.execution_cycles_remaining == 0:
                    inst_obj.ready_to_write = True
                    rob_entry.state = "Ready to Write"

                    result = None
                    if inst_obj.opname in ['ADD', 'SUB', 'OR', 'AND']:
                        val1 = rs.Vj if rs.Vj is not None else 0
                        val2 = rs.Vk if rs.Vk is not None else 0
                        if inst_obj.opname == 'ADD': result = val1 + val2
                        elif inst_obj.opname == 'SUB': result = val1 - val2
                        elif inst_obj.opname == 'OR': result = val1 | val2
                        elif inst_obj.opname == 'AND': result = val1 & val2
                    elif inst_obj.opname in ['MUL', 'DIV']:
                        val1 = rs.Vj if rs.Vj is not None else 0
                        val2 = rs.Vk if rs.Vk is not None else 0
                        if inst_obj.opname == 'MUL': result = val1 * val2
                        elif inst_obj.opname == 'DIV': 
                            if val2 != 0: result = val1 // val2
                            else: result = "DIV_BY_ZERO_ERROR"
                    elif inst_obj.opname in ['SLLI', 'SRLI']:
                        val = rs.Vj if rs.Vj is not None else 0
                        shift_amount = rs.Vk if rs.Vk is not None else 0 
                        if inst_obj.opname == 'SLLI': result = val << shift_amount
                        elif inst_obj.opname == 'SRLI': result = val >> shift_amount
                    elif inst_obj.opname in ['LW', 'LB']:
                        base_val = rs.Vj if rs.Vj is not None else 0
                        offset = inst_obj.address
                        effective_address = base_val + offset
                        result = self.memory[effective_address]
                    elif inst_obj.opname in ['SW', 'SB']:
                        base_reg_value = rs.Vj 
                        value_to_be_stored = rs.Vk 
                        offset = inst_obj.address 
                        effective_address = base_reg_value + offset
                        self.memory[effective_address] = value_to_be_stored
                        result = "MEM_STORED"
                    elif inst_obj.opname in ['BEQ', 'BNE']:
                        val1 = rs.Vj if rs.Vj is not None else 0
                        val2 = rs.Vk if rs.Vk is not None else 0
                        condition_met = (val1 == val2 if inst_obj.opname == 'BEQ' else val1 != val2)
                        rob_entry.actual_taken = PREDICT_TAKEN if condition_met else PREDICT_NOT_TAKEN
                        result = "BRANCH_EVALUATED"
                    
                    rob_entry.value = result


    # --- Estágio de Escrita de Resultado (Write Result - CDB) ---
    def write_result_stage(self):
        ready_to_write_robs = sorted([
            rob for rob in self.reorder_buffer 
            if rob.busy and rob.state == "Ready to Write" and rob.instruction.write_result_cycle == -1
        ], key=lambda x: x.id)

        if ready_to_write_robs:
            rob_entry_to_broadcast = ready_to_write_robs[0]
            
            rob_id_to_broadcast = rob_entry_to_broadcast.id
            result_value = rob_entry_to_broadcast.value
            inst_obj = rob_entry_to_broadcast.instruction
            
            inst_obj.write_result_cycle = self.current_cycle
            rob_entry_to_broadcast.state = "Write Result" 

            for rs in self.reservation_stations:
                if rs.busy:
                    if rs.Qj == rob_id_to_broadcast:
                        rs.Vj = result_value
                        rs.Qj = None
                    if rs.Qk == rob_id_to_broadcast:
                        rs.Vk = result_value
                        rs.Qk = None
            
            if rob_entry_to_broadcast.source_rs and rob_entry_to_broadcast.source_rs.busy:
                if rob_entry_to_broadcast.source_rs.destination_rob_id == rob_id_to_broadcast:
                    rob_entry_to_broadcast.source_rs.clear()

    # --- Estágio de Confirmação (Commit) ---
    def commit_stage(self):
        committed_this_cycle = False
        head_rob_entry = self.reorder_buffer[self.rob_head]

        if head_rob_entry.busy and head_rob_entry.state == "Write Result" and (head_rob_entry.instruction and head_rob_entry.instruction.commit_cycle == -1):
            head_rob_entry.state = "Commit" 
            head_rob_entry.instruction.commit_cycle = self.current_cycle
            committed_this_cycle = True
        
        elif head_rob_entry.busy and head_rob_entry.state == "Commit" and (head_rob_entry.instruction and head_rob_entry.instruction.commit_cycle == self.current_cycle -1): 
            inst_obj = head_rob_entry.instruction
            
            if head_rob_entry.inst_type == "BRANCH":
                predicted = head_rob_entry.predicted_taken
                actual = head_rob_entry.actual_taken

                if predicted != actual: 
                    print(f"!!! Misprediction de Branch em ROB ID {head_rob_entry.id} (Inst: {inst_obj})!")
                    
                    if actual == PREDICT_TAKEN:
                        self.program_counter = inst_obj.address
                    else:
                        self.program_counter = head_rob_entry.program_order_index + 1 
                    
                    rob_entries_to_clear_ids = []
                    temp_idx = (self.rob_head + 1) % len(self.reorder_buffer)
                    while temp_idx != self.rob_tail:
                        if self.reorder_buffer[temp_idx].busy:
                            rob_entries_to_clear_ids.append(temp_idx)
                        temp_idx = (temp_idx + 1) % len(self.reorder_buffer)

                    all_rob_ids_to_flush = set(rob_entries_to_clear_ids)
                    all_rob_ids_to_flush.add(head_rob_entry.id) 

                    for reg_name, reg_obj in self.register_file.items():
                        if reg_name == 'R0': 
                            reg_obj.value = 0
                            reg_obj.clear() 
                            continue

                        if reg_obj.busy:
                            if reg_obj.reorder_tag is None or reg_obj.reorder_tag in all_rob_ids_to_flush:
                                reg_obj.clear()

                    for clear_id in rob_entries_to_clear_ids:
                        rob_to_clear = self.reorder_buffer[clear_id]
                        rob_to_clear.clear() 

                    for rs in self.reservation_stations:
                        rs.clear()
                    
                    head_rob_entry.clear()
                    self.committed_instructions_count += 1
                    committed_this_cycle = True 

                    self.rob_head = (self.rob_head + 1) % len(self.reorder_buffer)
                    self.rob_tail = self.rob_head
                    self.current_rob_entries = 0
                    self.bubble_cycles += 1

                else: 
                    head_rob_entry.clear()
                    self.rob_head = (self.rob_head + 1) % len(self.reorder_buffer)
                    self.committed_instructions_count += 1
                    self.current_rob_entries -= 1
                    committed_this_cycle = True

            elif head_rob_entry.inst_type == "STORE":
                head_rob_entry.clear()
                self.rob_head = (self.rob_head + 1) % len(self.reorder_buffer)
                self.committed_instructions_count += 1
                self.current_rob_entries -= 1
                committed_this_cycle = True

            else: 
                dest_reg_name = head_rob_entry.destination_reg
                if dest_reg_name:
                    reg = self.register_file[dest_reg_name]
                    if reg.reorder_tag == head_rob_entry.id:
                        reg.value = head_rob_entry.value 
                        reg.clear() 
                head_rob_entry.clear()
                self.rob_head = (self.rob_head + 1) % len(self.reorder_buffer)
                self.committed_instructions_count += 1
                self.current_rob_entries -= 1
                committed_this_cycle = True
        
        return committed_this_cycle

    # --- NOVO: Função para Salvar o Estado Atual ---
    def save_current_state(self):
        # Cria uma cópia profunda do estado atual do objeto (exceto o histórico)
        current_state = copy.deepcopy(self.__dict__)
        if 'history' in current_state:
            del current_state['history'] # Não salvamos o histórico dentro do histórico
        self.history.append(current_state)

    # --- NOVO: Função para Voltar um Ciclo ---
    def step_back(self):
        if not self.history:
            return False
        
        # Recupera o último estado salvo
        previous_state = self.history.pop()
        
        # Restaura o dicionário interno do objeto com o estado anterior
        self.__dict__.update(previous_state)
        return True

    # Avanca o simulador em um ciclo de clock
    def clock_tick(self):
        # Salva o estado ANTES de executar qualquer mudança
        self.save_current_state()

        self.current_cycle += 1

        committed = self.commit_stage()
        self.write_result_stage()
        self.execute_stage()
        issued = self.issue_stage()

        if not issued and not committed and not self.is_finished():
            self.bubble_cycles += 1
        
        for entry in self.reorder_buffer:
            if entry.busy and entry.instruction:
                entry.instruction.state_at_cycle[self.current_cycle] = entry.state

    # Verifica se a simulação terminou
    def is_finished(self):
        is_all_issued = (self.program_counter >= self.program_length)
        is_rob_empty = (self.current_rob_entries == 0)
        return is_all_issued and is_rob_empty

    # Calcula e retorna as métricas de desempenho
    def get_metrics(self):
        total_cycles = self.current_cycle
        ipc = self.committed_instructions_count / total_cycles if total_cycles > 0 else 0
        return {
            "Total Cycles": total_cycles,
            "Committed Instructions": self.committed_instructions_count,
            "IPC": ipc,
            "Bubble Cycles": self.bubble_cycles,
            "Program Counter (PC)": self.program_counter,
        }

    # Reseta o simulador para o estado inicial
    def reset_simulator(self):
        self.register_file = {}
        self.memory = collections.defaultdict(int)
        self.program_counter = 0
        self.program_length = 0

        for rs in self.reservation_stations: rs.clear()
        for rob_pos in self.reorder_buffer: rob_pos.clear()
        
        self.rob_head = 0
        self.rob_tail = 0
        self.current_rob_entries = 0

        self.current_cycle = 0
        self.committed_instructions_count = 0
        self.bubble_cycles = 0
        self.is_running = False
        self.history.clear() # Limpa histórico ao resetar

# --- Classe TomasuloGUI ---
class TomasuloGUI:
    def __init__(self, master, simulator):
        self.master = master
        self.master.title("Simulador Tomasulo")
        self.simulator = simulator
        self.running_auto = False

        self._create_dummy_instructions_file()

        self.setup_ui()
        self.load_initial_program()

    def _create_dummy_instructions_file(self):
        filename = "instructions.txt"
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return

        with open(filename, "w") as f:
            f.write("""
# --- Teste de Previsao de Branch: Tomado (TAKEN) - Cenário de Misprediction ---
ADD R3, R1, R2          # R3 = 5 + 5 = 10
SUB R4, R3, R1          # R4 = 10 - 5 = 5
SUB R3, R3, R2          # R3 = 5 - 5 = 0
ADD R4, R3, R0          # R4 = 0 + 0 = 0
BEQ R4, R0, 7           # R4 (0) == R0 (0) --> DESVIA (TAKEN). Previsao NOT_TAKEN INCORRETA.
ADD R5, R1, R2          # Caminho SEQUENCIAL (sera limpo) - indice 5
MUL R5, R5, R0          # Caminho SEQUENCIAL (sera limpo) - indice 6
SUB R5, R1, R0          # Caminho do DESVIO (CORRETO) - indice 7
DIV R6, R1, R2          # Continua - indice 8
""")

    def setup_ui(self):
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

        left_frame = ttk.Frame(self.master, padding="10")
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=0)
        left_frame.grid_rowconfigure(2, weight=0)
        left_frame.grid_columnconfigure(0, weight=1)

        right_frame = ttk.Frame(self.master, padding="10")
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)
        right_frame.grid_rowconfigure(3, weight=1)
        for i in range(4):
            right_frame.grid_columnconfigure(i, weight=1)

        ttk.Label(left_frame, text="Programa de Instrucoes:").grid(row=0, column=0, sticky="nw", pady=(0, 5))
        self.program_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, height=15, width=40, state='disabled')
        self.program_text.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        control_frame = ttk.Frame(left_frame)
        control_frame.grid(row=1, column=0, sticky="ew", pady=(10, 5))
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)
        control_frame.columnconfigure(3, weight=1)
        control_frame.columnconfigure(4, weight=1) # Coluna extra para o novo botao

        # Botão Ciclo Anterior
        self.prev_cycle_button = ttk.Button(control_frame, text="Ciclo Anterior", command=self.prev_cycle, state="disabled")
        self.prev_cycle_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Botão Proximo Ciclo
        self.next_cycle_button = ttk.Button(control_frame, text="Proximo Ciclo", command=self.next_cycle)
        self.next_cycle_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.run_all_button = ttk.Button(control_frame, text="Executar Tudo", command=self.run_all)
        self.run_all_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.reset_button = ttk.Button(control_frame, text="Reiniciar", command=self.reset_simulation)
        self.reset_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        self.load_program_button = ttk.Button(control_frame, text="Carregar", command=self.load_initial_program)
        self.load_program_button.grid(row=0, column=4, padx=5, pady=5, sticky="ew")

        metrics_frame = ttk.LabelFrame(left_frame, text="Metricas de Desempenho", padding="10")
        metrics_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.metrics_labels = {}
        metrics_order = ["Total Cycles", "Committed Instructions", "IPC", "Bubble Cycles", "Program Counter (PC)"]
        for i, metric in enumerate(metrics_order):
            ttk.Label(metrics_frame, text=f"{metric}:").grid(row=i, column=0, sticky="w", padx=5, pady=2)
            value_label = ttk.Label(metrics_frame, text="0")
            value_label.grid(row=i, column=1, sticky="w", padx=5, pady=2)
            self.metrics_labels[metric] = value_label

        ttk.Label(right_frame, text="Buffer de Reordenacao (ROB):").grid(row=0, column=0, sticky="nw", pady=(0, 5), columnspan=4)
        self.rob_tree = self._create_treeview(right_frame, 
            ["ID", "Ocupado", "Instrucao", "Estado", "Reg. Dest.", "Valor", "Tipo", "Previsto", "Real"],
            {"ID": 40, "Ocupado": 60, "Instrucao": 150, "Estado": 100, "Reg. Dest.": 80, "Valor": 80, "Tipo": 60, "Previsto": 60, "Real": 60}
        )
        self.rob_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=(25, 10))

        ttk.Label(right_frame, text="Estacoes de Reserva (RS):").grid(row=1, column=0, sticky="nw", pady=(0, 5), columnspan=4)
        self.rs_tree = self._create_treeview(right_frame,
            ["Nome", "Ocupado", "Op", "Vj", "Vk", "Qj", "Qk", "ROB Dest."],
            {"Nome": 60, "Ocupado": 60, "Op": 50, "Vj": 70, "Vk": 70, "Qj": 50, "Qk": 50, "ROB Dest.": 80}
        )
        self.rs_tree.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(25, 10))

        ttk.Label(right_frame, text="Arquivo de Registradores:").grid(row=2, column=0, sticky="nw", pady=(0, 5), columnspan=2)
        self.reg_tree = self._create_treeview(right_frame,
            ["Registrador", "Valor", "Tag ROB", "Ocupado"],
            {"Registrador": 80, "Valor": 80, "Tag ROB": 70, "Ocupado": 60}
        )
        self.reg_tree.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(25, 10), padx=(0, 5))

        ttk.Label(right_frame, text="Memoria:").grid(row=2, column=2, sticky="nw", pady=(0, 5), columnspan=2)
        self.mem_tree = self._create_treeview(right_frame,
            ["Endereco", "Valor"],
            {"Endereco": 80, "Valor": 80}
        )
        self.mem_tree.grid(row=2, column=2, columnspan=2, sticky="nsew", pady=(25, 10), padx=(5, 0))

        self.update_gui()

    def _create_treeview(self, parent_frame, columns, widths):
        tree = ttk.Treeview(parent_frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=widths.get(col, 100), anchor="center")
        vsb = ttk.Scrollbar(parent_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid_configure(sticky="nsew")
        vsb.grid(row=tree.grid_info()['row'], column=tree.grid_info()['column']+len(columns)-1, 
                 rowspan=tree.grid_info()['rowspan'], sticky='ns')
        return tree

    def load_initial_program(self):
        self.simulator.reset_simulator()
        if self.simulator.load_instructions():
            self.program_text.config(state='normal')
            self.program_text.delete(1.0, tk.END)
            for idx, inst in enumerate(self.simulator.program_instructions):
                self.program_text.insert(tk.END, f"[{idx}]: {inst}\n")
            self.program_text.config(state='disabled')
            self.initial_program_loaded = True
            messagebox.showinfo("Sucesso", "Programa de instruções carregado com sucesso!")
        else:
            self.initial_program_loaded = False
        
        if 'R0' not in self.simulator.register_file: self.simulator.register_file['R0'] = Register('R0')
        self.simulator.register_file['R0'].value = 0 
        self.simulator.register_file['R0'].clear() 

        if 'R1' not in self.simulator.register_file: self.simulator.register_file['R1'] = Register('R1')
        self.simulator.register_file['R1'].value = 5
        if 'R2' not in self.simulator.register_file: self.simulator.register_file['R2'] = Register('R2')
        self.simulator.register_file['R2'].value = 5

        self.simulator.memory[108] = 5
        self.simulator.memory[16] = 0
        self.simulator.memory[12] = 7
        
        self.update_gui()

    # --- NOVO: Função chamada pelo botão "Ciclo Anterior" ---
    def prev_cycle(self):
        if not self.initial_program_loaded:
            return
        
        success = self.simulator.step_back()
        if success:
            self.running_auto = False # Para execução automática se voltar
            self.update_gui()
        else:
            messagebox.showinfo("Info", "Início da simulação alcançado.")

    def next_cycle(self):
        if not self.initial_program_loaded:
            messagebox.showwarning("Aviso", "Por favor, carregue um programa primeiro.")
            return

        if not self.simulator.is_finished():
            self.simulator.clock_tick()
            self.update_gui()
            if self.simulator.is_finished():
                messagebox.showinfo("Simulação Concluída", "Todas as instruções foram processadas!")
                self.running_auto = False 
        else:
            messagebox.showinfo("Simulação Concluída", "Todas as instruções já foram processadas!")
            self.running_auto = False

    def run_all(self):
        if not self.initial_program_loaded:
            messagebox.showwarning("Aviso", "Por favor, carregue um programa primeiro.")
            return
        
        self.running_auto = True
        self._run_all_cycles()

    def _run_all_cycles(self):
        if self.running_auto and not self.simulator.is_finished():
            self.simulator.clock_tick()
            self.update_gui()
            self.master.after(100, self._run_all_cycles)
        elif self.simulator.is_finished():
            messagebox.showinfo("Simulação Concluída", "Todas as instruções foram processadas!")
            self.running_auto = False

    def reset_simulation(self):
        self.running_auto = False
        self.simulator.reset_simulator()
        self.load_initial_program()
        messagebox.showinfo("Reiniciar", "Simulação reiniciada.")

    def update_gui(self):
        # Habilita ou desabilita o botão "Ciclo Anterior" baseado no histórico
        if hasattr(self, 'prev_cycle_button'):
            if self.simulator.current_cycle > 0 and self.simulator.history:
                self.prev_cycle_button.config(state="normal")
            else:
                self.prev_cycle_button.config(state="disabled")

        for i in self.rob_tree.get_children():
            self.rob_tree.delete(i)
        for entry in self.simulator.reorder_buffer:
            self.rob_tree.insert("", "end", values=(
                entry.id,
                "Sim" if entry.busy else "Não",
                str(entry.instruction) if entry.instruction else "",
                entry.state,
                str(entry.destination_reg) if entry.destination_reg else "",
                str(entry.value) if entry.value is not None else "",
                entry.inst_type,
                "T" if entry.predicted_taken == PREDICT_TAKEN else ("NT" if entry.predicted_taken == PREDICT_NOT_TAKEN else ""),
                "T" if entry.actual_taken == PREDICT_TAKEN else ("NT" if entry.actual_taken == PREDICT_NOT_TAKEN else "")
            ))
        
        for i in self.rs_tree.get_children():
            self.rs_tree.delete(i)
        for rs in self.simulator.reservation_stations:
            self.rs_tree.insert("", "end", values=(
                rs.name,
                "Sim" if rs.busy else "Não",
                str(rs.op) if rs.op else "",
                str(rs.Vj) if rs.Vj is not None else "",
                str(rs.Vk) if rs.Vk is not None else "",
                str(rs.Qj) if rs.Qj is not None else "",
                str(rs.Qk) if rs.Qk is not None else "",
                str(rs.destination_rob_id) if rs.destination_rob_id is not None else ""
            ))

        for i in self.reg_tree.get_children():
            self.reg_tree.delete(i)
        sorted_regs = sorted(self.simulator.register_file.values(), key=lambda r: r.name)
        for reg in sorted_regs:
            self.reg_tree.insert("", "end", values=(
                reg.name,
                str(reg.value),
                str(reg.reorder_tag) if reg.reorder_tag is not None else "",
                "Sim" if reg.busy else "Não"
            ))

        for i in self.mem_tree.get_children():
            self.mem_tree.delete(i)
        accessed_memory = sorted([addr for addr, val in self.simulator.memory.items() if val != 0 or addr in [108, 211, 16, 12]])
        for addr in accessed_memory: 
            self.mem_tree.insert("", "end", values=(f"End. {addr}", self.simulator.memory[addr]))
        for i in range(5):
             if i not in accessed_memory:
                 self.mem_tree.insert("", "end", values=(f"End. {i}", self.simulator.memory[i]))


        metrics = self.simulator.get_metrics()
        self.metrics_labels["Total Cycles"].config(text=str(metrics["Total Cycles"]))
        self.metrics_labels["Committed Instructions"].config(text=str(metrics["Committed Instructions"]))
        self.metrics_labels["IPC"].config(text=f"{metrics['IPC']:.2f}")
        self.metrics_labels["Bubble Cycles"].config(text=str(metrics["Bubble Cycles"]))
        self.metrics_labels["Program Counter (PC)"].config(text=str(self.simulator.program_counter))


        self.program_text.config(state='normal')
        for tag in self.program_text.tag_names():
            if tag.startswith("state_") or tag == "highlight":
                self.program_text.tag_remove(tag, "1.0", tk.END)

        if self.simulator.program_counter < len(self.simulator.program_instructions):
            line_number = self.simulator.program_counter + 1
            self.program_text.tag_add("highlight", f"{line_number}.0", f"{line_number}.end")
            self.program_text.tag_config("highlight", background="yellow")
        
        self.program_text.config(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    simulator_instance = TomasuloSimulator()
    gui = TomasuloGUI(root, simulator_instance)
    root.mainloop()