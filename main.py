WIDTH = 32
class ZeroTouchGround(list):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().__setitem__(0, 0)

class Registers:
    def __init__(self):
        self._regs = ZeroTouchGround([0] * WIDTH)
        # for i in range(WIDTH):
        #     self._regs[i] = i
        self.name_map = {
            'zero': 0, 'at': 1, 'v0': 2, 'v1': 3,
            'a0': 4, 'a1': 5, 'a2': 6, 'a3': 7,
            't0': 8, 't1': 9, 't2': 10, 't3': 11, 't4': 12, 't5': 13, 't6': 14, 't7': 15,
            's0': 16, 's1': 17, 's2': 18, 's3': 19, 's4': 20, 's5': 21, 's6': 22, 's7': 23,
            't8': 24, 't9': 25, 'k0': 26, 'k1': 27, 'gp': 28, 'sp': 29, 'fp': 30, 'ra': 31
        }
    def write_register(self, index, value):
        self._regs[index] = value
    def read_register(self, index):
        return self._regs[index]
    def dump(self):
        changed = {f"${name}": self._regs[idx] for name, idx in self.name_map.items()}
        return changed
class Memory:
    def __init__(self):
        self.storage = {}
    def read(self, address):
        if address < 0 or address >= 0xFFFFFFFF:
            raise Exception(f"OutOfBoundsError: Cannot read out of bounds memory{hex(address)}")
        if address%4 != 0:
            raise Exception(f"Alignment Error: Cannot read word from unaligned address {hex(address)}")
        return self.storage.get(address, 0)
    def write(self, address, value):
        if address < 0 or address >= 0xFFFFFFFF:
            raise Exception(f"OutOfBoundsError: Cannot write memory out of bounds{hex(address)}")
        if address%4 != 0:
            raise Exception(f"Alignment Error: Cannot write word to unaligned address {hex(address)}")
        print(f"Writing value {value} to address {hex(address)}")
        self.storage[address] = value& 0xFFFFFFFF
        print(self.storage)

class CPUCore:
    def __init__(self):
        self.registers = Registers()
        self.alu = ALU()
        self.pc = 0x00400000 #Program_Counter
        self.memory = Memory()
        self.overflow = 0
        self.exception = None
    def get_bits(self,val, start, end): #support function to extract bits from a value
        length = end - start + 1
        mask = (1 << length) - 1
        return (val >> start) & mask
    def execute(self):
        # ===IF===
        bin_code = self.Instruction_MEM(self.pc)
        pc = self.pc + 4
        # ===ID===
        print(f"Executing instruction: {bin_code:032b}")
        # print(f"self.get_bits(bin_code, 0, 5): {self.get_bits(bin_code, 26, 31):06b}")
        control_signals = self.control_unit(self.get_bits(bin_code, 26, 31))
        rData1 = self.registers.read_register(self.get_bits(bin_code, 21, 25))
        rData2 = self.registers.read_register(self.get_bits(bin_code, 16, 20))
        rd_index = self.get_bits(bin_code, 11, 15)
        # print(f"rs({self.get_bits(bin_code, 21, 25)}): {rData1}, rt({self.get_bits(bin_code, 16, 20)}): {rData2}")

        immt = self.get_bits(bin_code, 0, 15)
        sign_bit = (immt >> 15) & 1
        for i in range(16): #signed extension 16-bit to 32-bit
            immt |= sign_bit << i+16
        # print(f"imm: {immt}")
        # ===EX===
        alu_input = rData2
        # print(control_signals["alu_src"])
        if control_signals["alu_src"]:  #alu_src multiplexor
            alu_input = immt  # immediate value
            # print(f"ALUSrc is 1, using constant {op_b} as op_b")
        # print(f"rData1: {rData1}, rData2: {rData2},alu_input: {alu_input}, opcode: {self.get_bits(bin_code, 0, 5)}, alu_op1: {control_signals['alu_op1']}, alu_op0: {control_signals['alu_op0']}")
        result, zero_flag, self.overflow = self.alu.execute(rData1, alu_input, self.get_bits(bin_code, 0, 5), control_signals["alu_op1"], control_signals["alu_op0"])
        # print(f"ALU result: {result}, zero_flag: {zero_flag}")
        if self.overflow:
            print("Overflow occurred. Result not written to register.")
            self.overflow = 0  # Reset overflow flag after handling
            return
        # ===MEM===
        rMData = 0
        rMData = self.Data_Memory(result, rData2, control_signals["mem_read"], control_signals["mem_write"])
        if control_signals["mem_to_reg"]:
            print(f"Memory read: {rMData} from address {result}")
            result = rMData
        # ===WB===
        if self.exception:
            print(f"Exception: {self.exception}")
            return

        # print(control_signals["reg_dst"])
        if control_signals["reg_dst"]:
            regd = rd_index
        else:
            regd = self.get_bits(bin_code, 16, 20)
        # print(f"Writing to register index {regd} with value {result}")
        if control_signals["reg_write"]:
            self.registers.write_register(regd, result)
        self.pc = pc
    def Instruction_MEM(self, address):
        instruction = self.memory.read(address)
        return instruction
    def control_unit(self, opcode):
        signals ={
            "reg_dst": 0,
            "alu_src": 0,
            "mem_to_reg": 0,
            "reg_write": 0,
            "mem_read": 0,
            "mem_write": 0,
            "branch": 0,
            "ext_op": 0,
            "alu_op1": 0,
            "alu_op0": 0
        }
        op = []
        for i in range(6):
            op.append(opcode & (1<<5-i))
        r_type, lw, sw, beq, addi = 0,0,0,0,0
        r_type = (not op[5]) and (not op[4]) and (not op[3]) and (not op[2]) and (not op[1]) and (not op[0]) #000000
        lw = op[5] and op[4] and (not op[3]) and (not op[2]) and (not op[1]) and op[0] #100011
        sw = op[5] and op[4] and (not op[3]) and op[2] and (not op[1]) and op[0] #101011
        beq = (not op[5]) and (not op[4]) and op[3] and (not op[2]) and (not op[1]) and (not op[0]) #000100
        addi = (not op[5]) and (not op[4]) and (not op[3]) and op[2] and (not op[1]) and (not op[0]) #00100
        # r_type = bool(r_type)
        # lw = bool(lw)
        # sw = bool(sw)
        # beq = bool(beq)
        signals["reg_dst"] = r_type
        signals["alu_src"] = (lw or sw or addi)
        signals["mem_to_reg"] = lw
        signals["reg_write"] = (r_type or lw or addi)
        signals["mem_read"] = lw
        signals["mem_write"] = sw
        signals["branch"] = beq
        signals["ext_op"] = 0
        signals["alu_op1"] = r_type
        signals["alu_op0"] = beq
        for key,value in signals.items():
            signals[key] = 1 if value else 0 # Formatting for clear looks <3
        # print(f"op: {op}")
        # print(f"r_type: {r_type}, lw: {lw}, sw: {sw}, beq: {beq}")
        # print(f"control_unit: {signals}")
        return signals
    def Data_Memory(self, address, write_data, mem_read, mem_write):
        if mem_read:
            return self.memory.read(address)
        if mem_write:
            self.memory.write(address, write_data)
            return 0
class ALU:
    def __init__(self):
        self.exception = None
        self.overflow = 0
    def execute(self,rData1, rData2, func_code,alu_op1, alu_op0):
        ALU_control_signals = self.ALU_control_unit(func_code, alu_op1, alu_op0)
        # print(f"ALU control signals: {ALU_control_signals}")
        alu_result, zero_flag, overflow = self.ALU_32(ALU_control_signals, rData1, rData2)
        return alu_result, zero_flag, overflow
    def ALU_control_unit(self, func_code,alu_op1, alu_op0):
        # print(f"ALU_control_unit: func_code={func_code}, alu_op1={alu_op1}, alu_op0={alu_op0}")
        signals = [0] * 4 # [ainvert,binvert, op1, op0]
        if alu_op1 == 0 and alu_op0 == 0:
            signals[2] = 1 #add
        if alu_op1 ==1 and alu_op0 == 0:
            if func_code == 0b100100: #and
                # do nothing, default is [0,0,0,0]
                pass
            elif func_code == 0b100101: #or
                signals[3] = 1
            elif func_code == 0b100000: #add
                signals[2] = 1
            elif func_code == 0b100010: #sub
                signals[1] = 1
                signals[2] = 1
            elif func_code == 0b100111: #nor
                signals[0] = 1
                signals[1] = 1
            elif func_code == 0b101010: #slt
                signals[1] = 1
                signals[2] = 1
                signals[3] = 1
        return signals
    def ALU_32(self, table, op_a, op_b):
        op_a = op_a & 0xFFFFFFFF
        op_b = op_b & 0xFFFFFFFF
        result = 0x0
        carry_in = 0
        zero_flag = 0
        for i in range(WIDTH):
            bit_a = (op_a >> i) & 1
            bit_b = (op_b >> i) & 1
            if i == 0:
                carry_in = table[1] #carry_in = binvert in first round
            if i == WIDTH-1:
                last_carry_in = carry_in
            result_bit, carry_in = self.ALU_01(table, bit_a, bit_b, carry_in)
            result |= result_bit<<i
            # print(f"ALU_32: carry_in={carry_in}, result_bit={result_bit}, result={result}")
        overflow_flag = carry_in ^ last_carry_in
        if table[2] and table[3]:  # SLT operation
            # print(f"ALU_32: SLT operation, carry_out={carry_in}, before_result={result}, zero_flag={zero_flag}, overflow_flag={overflow_flag}, result_bit={result_bit}")
            result = result_bit^overflow_flag
            self.overflow = 0
        if result == 0: #and all bits are zero, set zero_flag
            zero_flag = 1
        if overflow_flag:
            self.overflow = 1
        return result & 0xFFFFFFFF, zero_flag, self.overflow
        
    def ALU_01(self, table, op_a, op_b, carry_in): #table: [ainvert, binvert, op1, op0]
        carry_out = 0
        # print(f"ALU_01: op_a={op_a}, op_b={op_b}, carry_in={carry_in}")

        if table[0]: op_a = (~op_a)&1
        if table[1]: op_b = (~op_b)&1
        gate_and = op_a & op_b
        gate_or = op_a | op_b
        gate_add = op_a + op_b + carry_in
        carry_out = 1 if (gate_add) > 1 else 0
        gate_add = gate_add % 2
        if table[2] == 0:
            if table[3] ==0:
                return gate_and, carry_out # and
            return gate_or, carry_out # or
        if table[2]:
            result_bit = gate_add
            return result_bit%2, carry_out
        else:
            self.exception = "Invalid ALU operation"
class Compiler:
    def __init__(self, registers):
        self.reg_table = registers
        self.exception = None
        self.nop = 0
        self.inst_map = {
            'add':  (0b000000, 0b100000, 'R'),
            'sub':  (0b000000, 0b100010, 'R'),
            'and':  (0b000000, 0b100100, 'R'),
            'or':   (0b000000, 0b100101, 'R'),
            'nor':  (0b000000, 0b100111, 'R'),
            'slt':  (0b000000, 0b101010, 'R'),
            'sll':  (0b000000, 0b000000, 'R'),

            'addi': (0b001000, 0b000000, 'I'),
            'lw':   (0b100011, 0b000000, 'I'),
            'sw':   (0b101011, 0b000000, 'I'),
            'beq':  (0b000100, 0b000000, 'I'),
        }
    def compile_r_type(self, cmd,bin_code,func_code): #R-type[inst rd rs rt/shamt]
        if len(cmd) < 4:
            self.exception = "Invalid R-type instruction format"
            bin_code = self.nop
            return bin_code
        rd,rs,rt,shamt = 0,0,0,0
        try:
            rd = self.reg_table.name_map[cmd[1]]
            rs = self.reg_table.name_map[cmd[2]] # op:6, rs:5, rt:5, rd:5, shamt:5, other:6
            try:
                shamt = int(cmd[3]) & 0x1F
            except ValueError:
                shamt = 0
                rt = self.reg_table.name_map[cmd[3]]
        except KeyError:
            self.exception = "Invalid R-type instruction format"
            bin_code = self.nop
            return bin_code
        bin_code |= rs << 21
        bin_code |= rt << 16
        bin_code |= rd << 11
        bin_code |= shamt << 6
        bin_code |= func_code
        # print(f"bin_code after R-type: {bin_code:032b}")
        return bin_code
    def compile_i_type(self, cmd,bin_code): #I-type[inst rt rs imm]
        if cmd[2].find("(") != -1 and cmd[2].find(")") != -1: #lw/sw format: lw $t0, 4($t1)
            cmd.insert(3, cmd[2].split("(")[0])
            cmd[2] = cmd[2].split("(")[1].split(")")[0]
        # print(f"cmd after parsing: {cmd}")
        if len(cmd) < 4:
            self.exception = "Invalid I-type instruction format: Not enough arguments"
            bin_code = self.nop
            return bin_code

        rt,rs,imm = 0,0,0
        try:
            rt = self.reg_table.name_map[cmd[1]]
            rs = self.reg_table.name_map[cmd[2]] # op:6, rs:5, rt:5, rd:5, shamt:5, other:6
            try:
                imm = int(cmd[3]) & 0xFFFF
            except ValueError:
                try:
                    imm = int(cmd[3], 16) & 0xFFFF
                except ValueError:
                    imm = 0
                    print(f"Invalid immediate value: {cmd[3]}. Defaulting to 0.")
                    rt = self.reg_table.name_map[cmd[3]]
        except KeyError:
            self.exception = "Invalid I-type instruction format: Invalid register name"
            bin_code = self.nop
            return bin_code
        bin_code |= rs << 21
        bin_code |= rt << 16
        bin_code |= imm
        # print(f"bin_code after I-type: {bin_code:032b}")
        return bin_code
    def compile(self, cmd):
        cmd = cmd.split("#")[0]  # Remove comments
        cmd = cmd.replace("$", "").replace(",", " ").replace("\t", " ").strip().split()
        if not cmd:
            self.exception = "Empty command"
            return self.nop
        print(f"Decoded command: {cmd}")

        bin_code = 0
        # print(f"bincode={bin_code[:6]}:{bin_code[6:11]}:{bin_code[11:16]}:{bin_code[16:21]}:{bin_code[21:26]}:{bin_code[26:]}")
        # bin_code = self.registers_to_bin(cmd, bin_code)
        # print(f"bincode={bin_code[:6]}:{bin_code[6:11]}:{bin_code[11:16]}:{bin_code[16:21]}:{bin_code[21:26]}:{bin_code[26:]}")
        inst = cmd[0].lower()
        opcode = 0b000000
        inst_type = None
        func_code = 0b000000
        if inst in self.inst_map:
            opcode, func_code, inst_type = self.inst_map[inst]
        else:
            self.exception = "Invalid instruction"
            bin_code = self.nop
            return bin_code
        bin_code |= opcode << WIDTH - 6
        # print(f"bin_code after opcode: {bin_code:032b}")
        # print(f"Opcode: {opcode:06b}, Function code: {func_code:06b}, Instruction type: {inst_type}")
        match  inst_type:
            case 'R': 
                bin_code = self.compile_r_type(cmd, bin_code,func_code)
            case 'I':
                bin_code = self.compile_i_type(cmd, bin_code)
            case _:
                self.exception = "Invalid instruction type"
                bin_code = self.nop
        return bin_code

class Loader:
    def __init__(self, CPU):
        self.CPU = CPU
        self.registers = CPU.registers
        self.memory = CPU.memory
        self.SP = 0x7FFFFFFC
        self.GP = 0x10008000
        self.PC = 0x00400000
    def load_program(self, program):
        self.registers.write_register(self.registers.name_map['sp'], self.SP)
        self.registers.write_register(self.registers.name_map['gp'], self.GP)
        self.CPU.pc = self.PC
        for i, instruction in enumerate(program):
            address = self.PC + i * 4
            self.memory.write(address, instruction)
def interface():
    CPU = CPUCore()
    registers = CPU.registers
    compiler_32 = Compiler(registers)
    loader = Loader(CPU)
    code = """
        addi $t0, $zero, 5
        addi $t1, $zero, 3
        add $t2, $t0, $t1
        sw $t2, 0($zero)
        lw $t3, 0($zero)
    """
    code = """
addi $s0, $zero, 0x1234 # $s0 = 0x1234
addi $s1, $zero, 0x5678 # $s1 = 0x5678
sw   $s0, 4($zero)      # write 0x1234 to Memory[4]
sw   $s1, 8($zero)      # write 0x5678 to Memory[8]
lw   $s2, 4($zero)      # read from Memory[4] to $s2
lw   $s3, 8($zero)      # read from Memory[8] to $s3

"""
    code = """
addi $s0, $zero, 1     # F(1) = 1
addi $s1, $zero, 1     # F(2) = 1
addi $sp, $zero, 100   # push stack pointer to 100

sw   $s0, 0($sp)       # Memory[100] = 1
sw   $s1, 4($sp)       # Memory[104] = 1

# Calculate F(3)
add  $s2, $s0, $s1     # $s2 = 1 + 1 = 2
sw   $s2, 8($sp)       # Memory[108] = 2

# Calculate F(4)
add  $s0, $s1, $s2     # $s0 = 1 + 2 = 3
sw   $s0, 12($sp)      # Memory[112] = 3

# Calculate F(5)
add  $s1, $s2, $s0     # $s1 = 2 + 3 = 5
sw   $s1, 16($sp)      # Memory[116] = 5
"""

    program = []
    print("Welcome to the command line interface. Type 'exit' to quit.")
    while (True):
        try:
            cmd = input("$ ")
        except KeyboardInterrupt:
            print("\nExiting the program.")
            break
        if cmd.lower() == 'exit':
            print("Exiting the program.")
            break
        if cmd == "":
            continue
        if cmd == "registers" or cmd == "regs":
            display = registers.dump()
            for i in range(0, len(display), 4):
                
                print(" ".join(f"{k}: {v:032b}" for k, v in list(display.items())[i:i+4]))
            continue
        for i in range(0, len(code.splitlines())):
            line = code.splitlines()[i]
            if line.strip() == "":
                continue
            # print(f"Compiling instruction {i}: {line}")
            machine_code = compiler_32.compile(line)
            program.append(machine_code)
        if compiler_32.exception:
            print(f"Error: {compiler_32.exception}")
            compiler_32.exception = None
            continue
        loader.load_program(program)
        for i in range(len(program)):
            print(f"Instruction {i}: {program[i]:032b}")
            CPU.execute()
            if CPU.exception:
                print(f"Error: {CPU.exception}")
                CPU.exception = None
                continue
            display = registers.dump()

        for i in range(0, len(display), 4):
            print(" ".join(f"{k}: {v}" for k, v in list(display.items())[i:i+4]))



if __name__ == "__main__":
        interface()