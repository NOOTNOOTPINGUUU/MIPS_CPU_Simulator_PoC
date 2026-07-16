WIDTH = 32
def get_bits(val, start, end): #support function to extract bits from a value
    length = end - start + 1
    mask = (1 << length) - 1
    return (val >> start) & mask
class AutoZeroDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in list(self.items()):
            if isinstance(value, dict) and not isinstance(value, AutoZeroDict):
                self[key] = AutoZeroDict(value)

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            return AutoZero()

    def copy(self):

        new_copied_dict = AutoZeroDict()
        for key, value in self.items():
            if isinstance(value, AutoZeroDict):
                new_copied_dict[key] = value.copy()
            else:
                new_copied_dict[key] = value
        return new_copied_dict
class AutoZero(int):
    def __new__(cls):
        return super().__new__(cls, 0)
    def __getitem__(self, item):
        return self
    def get(self, item, default=0):
        return self

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
        self.dump_storage = {}
    def read_byte(self, address):
        return self.storage.get(address, 0)&0xFF
    def read(self, address):
        byte_value = 0
        # byte_value = self.storage.get(address, 0)&0xFFFFFFFF
        # if address < 0 or address >= 0xFFFFFFFF:
        #     raise Exception(f"OutOfBoundsError: Cannot read out of bounds memory{hex(address)}")
        # if address%4 != 0:
        #     raise Exception(f"Alignment Error: Cannot read word from unaligned address {hex(address)}")
        for i in range(4):
            byte_value |= (self.read_byte(address + 3 - i) << ((3 - i) * 8))
            # print(f"Reading byte {hex(self.storage.get(address + 3-i, 0)&0xFF)} from address {hex(address + 3-i)}")
        # print(f"Reading value {hex(byte_value)} from address {hex(address)}")
        return byte_value
    def write(self, address, value):
        # if address < 0 or address >= 0xFFFFFFFF:
        #     raise Exception(f"OutOfBoundsError: Cannot write memory out of bounds{hex(address)}")
        # if address%4 != 0:
        #     raise Exception(f"Alignment Error: Cannot write word to unaligned address {hex(address)}")
        # print(f"Writing value {value} to address {hex(address)}")
        for i in range(4):
            byte_value = (value >> (i * 8))& 0xFF
            self.storage[address + i] = byte_value
        self.dump_storage[address] = value& 0xFFFFFFFF
        # print(self.storage)
    def dump(self):
        changed = {f"M[{hex(k)}]": v for k, v in self.storage.items()}
        return changed
class CP0:
    def __init__(self):
        self._regs = ZeroTouchGround([0]*WIDTH)
        self.name_map = {
            'BadVAddr': 8, 
            'Status': 12,   #UM|EXL 
            'Cause': 13,
            'EPC': 14
        }
    def write_register(self, index, value):
        EXL = get_bits(self.read_register(self.name_map['Status']), 1, 1)
        if index == self.name_map['EPC'] and EXL:
            return
        self._regs[index] = value
    def read_register(self, index):
        return self._regs[index]
    def to_user_mode(self):
        self.write_register(self.name_map['Status'], (self._regs[self.name_map['Status']] & ~0b10010) | 0b10000)
    def to_exception_mode(self):
        self.write_register(self.name_map['Status'], (self._regs[self.name_map['Status']] & ~0b10) | 0b10)
    def eret(self):
        self.write_register(self.name_map['Status'], (self._regs[self.name_map['Status']] & ~0b10) | 0b00)
    def dump(self):
        changed = {f"{name}": self._regs[idx] for name, idx in self.name_map.items()}
        return changed

class StagePipelineRegister:
    def __init__(self):
        self.current = AutoZeroDict()
        self.next = AutoZeroDict()
        self.flush_signal = 0
    def read(self):
        return self.current
    def write(self,data):
        self.next = AutoZeroDict(data)
    def tick(self):
        if self.flush_signal:
            self.current = AutoZeroDict()
            self.flush_signal = 0
        else:
            self.current = self.next.copy()
    def flush(self):
        self.flush_signal = 1
class Forwarding_Unit:
    def __init__(self):
        self.ex_mem_RegWrite = 0
        self.mem_wb_RegWrite = 0
        self.ex_mem_RegDst = 0
        self.mem_wb_RegDst = 0
        self.id_ex_rs = 0
        self.id_ex_rt = 0



    def determine_forwarding_paths(self ,id_ex_rs ,id_ex_rt):
        self.id_ex_rs = id_ex_rs
        self.id_ex_rt = id_ex_rt
        FW_A = 0
        FW_B = 0
        #ReadAfterWrite
        # MEM_WB        
        if self.mem_wb_RegWrite ==1 and self.mem_wb_RegDst !=0:
            if self.mem_wb_RegDst == self.id_ex_rs:
                FW_A = 1
            if self.mem_wb_RegDst == self.id_ex_rt:
                FW_B = 1
        # EX_MEM
        if self.ex_mem_RegWrite ==1 and self.ex_mem_RegDst !=0:
            if self.ex_mem_RegDst == self.id_ex_rs:
                FW_A = 2
            if self.ex_mem_RegDst == self.id_ex_rt:
                FW_B = 2
        # print(f"FW_A: {FW_A}, FW_B: {FW_B}, id_ex_rs: {id_ex_rs}, id_ex_rt: {id_ex_rt}, mem_wb_RegWrite: {self.mem_wb_RegWrite}, mem_wb_RegDst: {self.mem_wb_RegDst}, ex_mem_RegWrite: {self.ex_mem_RegWrite}, ex_mem_RegDst: {self.ex_mem_RegDst}")
        return FW_A, FW_B
class Pipelined_CPUCore:
    def __init__(self):
        self.IF_ID = StagePipelineRegister()
        self.ID_EX = StagePipelineRegister()
        self.EX_MEM = StagePipelineRegister()
        self.MEM_WB = StagePipelineRegister()
        self.registers = Registers()
        self.alu = ALU()
        self.cp0 = CP0()
        self.pc = 0x00400000 #Program_Counter
        self.memory = Memory()
        
        self.overflow = 0
        
        self.exception = None
        self.EV_ADDRESS = 0x80000180 # Exception Vector Address
        self.cp0.to_user_mode()

        # IF_control_Hazard
        self.PCSrcJ = 0
        self.PCSrcB = 0
        self.PCSrc_Exception = 0
        self.Forward_AddrJ = 0
        self.Forward_AddrB = 0

        self.Forwarding_unit = Forwarding_Unit()
        # EX_forwarding_unit
        self.Forward_EX_MEM_data = 0
        self.Forward_MEM_WB_data = 0

    def IF(self):
        bin_code = self.Instruction_MEM(self.pc)
        EXL = get_bits(self.cp0.read_register(self.cp0.name_map['Status']), 1, 1)
        UM = get_bits(self.cp0.read_register(self.cp0.name_map['Status']), 4, 4)
        EX_CODE = 0x00
        EPC = self.pc
        pc = self.pc + 4
        print(f"PC: {hex(self.pc)}, Instruction: {bin_code:032b}, EXL: {EXL}, UM: {UM}, EX_CODE: {EX_CODE}")
        
        self.pc = pc
        if self.PCSrcB == 1:
            self.pc = self.Forward_AddrB
            self.PCSrcB = 0
            self.IF_ID.flush()
        if self.PCSrcJ == 1:
            self.pc = self.Forward_AddrJ
            self.PCSrcJ = 0
            self.IF_ID.flush()
        if self.PCSrc_Exception == 1:
            self.pc = self.EV_ADDRESS
            self.PCSrc_Exception = 0

        return {
            "bin_code": bin_code,
            "EXL": EXL,
            "UM": UM,
            "EX_CODE": EX_CODE,
            "EPC": EPC,
            "pc": pc,
        }
        # print(f"EXL: {EXL}, UM: {UM}, EX_CODE: {EX_CODE}")
    def ID(self, if_info):
        bin_code = if_info["bin_code"]
        EXL = if_info["EXL"]
        UM = if_info["UM"]
        EX_CODE = if_info["EX_CODE"]
        pc = if_info["pc"]

        # print(f"get_bits(bin_code, 0, 5): {get_bits(bin_code, 26, 31):06b}")
        control_signals = self.control_unit(get_bits(bin_code, 26, 31))
        # print(f"Control signals: {control_signals}")
        if get_bits(bin_code, 26, 31) == 0 and get_bits(bin_code, 0, 5) == 0b001100:
            # print(f"Syscall detected")
            # display = self.registers.dump()
            # for i in range(0, len(display), 4):
            #     print(" ".join(f"{k}: {hex(v)}" for k, v in list(display.items())[i:i+4]))
            EX_CODE = 0x08
            # self.cp0.to_exception_mode()
            control_signals["reg_write"] = 0
            control_signals["mem_write"] = 0
        rs_index = get_bits(bin_code, 21, 25)
        rt_index = get_bits(bin_code, 16, 20)
        rd_index = get_bits(bin_code, 11, 15)

        rData1 = self.registers.read_register(rs_index)
        rData2 = self.registers.read_register(rt_index)

        immt = get_bits(bin_code, 0, 15)
        sign_bit = (immt >> 15) & 1
        if control_signals["sign_ext"]:
            if sign_bit == 1:
                immt |= 0xFFFF0000 #sign extend
            else:
                immt &= 0x0000FFFF #zero extend
        # print(f"imm: {immt}")

        # Branch

        branch_address = immt << 2
        branch_address = (pc + branch_address)& 0xFFFFFFFF
        if control_signals["branch"] and rData1 == rData2:
            self.PCSrcB = 1
            self.Forward_AddrB = branch_address
        
        jAddress = get_bits(bin_code, 0, 25)
        jAddress = jAddress << 2
        jAddress = (get_bits(self.pc, 28, 31) << 28) | jAddress
        if control_signals["jump"]:
            self.PCSrcJ = 1
            self.Forward_AddrJ = jAddress
            
        return {
            "EXL": EXL,
            "UM": UM,
            "EX_CODE": EX_CODE,
            "EPC": if_info["EPC"],
            "WB_signals":{"reg_write":control_signals["reg_write"]},
            "MEM_signals":{"mem_read":control_signals["mem_read"],"mem_write":control_signals["mem_write"]},
            "EX_signals":{"alu_op":control_signals["alu_op"],"alu_src":control_signals["alu_src"],"reg_dst":control_signals["reg_dst"],
                        },
            "rData1": rData1,
            "rData2": rData2,
            "immt": immt,
            "rs_index": rs_index,
            "rd_index": rd_index,
            "rt_index": rt_index,
            "pc": if_info["pc"]
        }
    def EX(self, id_info):
        EX_CODE = id_info["EX_CODE"]
        WB_signals = id_info["WB_signals"]
        MEM_signals = id_info["MEM_signals"]
        EX_signals = id_info["EX_signals"]
        rData1 = id_info["rData1"]
        rData2 = id_info["rData2"]
        immt = id_info["immt"]
        rs_index = id_info["rs_index"]
        rd_index = id_info["rd_index"]
        rt_index = id_info["rt_index"]
        pc = id_info["pc"]
        
        alu_inputA = rData1
        alu_inputB = rData2
        # print(control_signals["alu_src"])

        
        FW_A, FW_B = self.Forwarding_unit.determine_forwarding_paths(rs_index, rt_index)
        # print(f"Forwarding A: {FW_A}, Forwarding B: {FW_B}, rData1: {rs_index}:{rData1}, rData2: {rt_index}:{rData2}")
        if FW_A == 2:
            alu_inputA = self.Forward_EX_MEM_data
        elif FW_A == 1:
            alu_inputA = self.Forward_MEM_WB_data
        if FW_B == 2:
            alu_inputB = self.Forward_EX_MEM_data
        elif FW_B == 1:
            alu_inputB = self.Forward_MEM_WB_data
        if EX_signals["alu_src"]:  #alu_src multiplexor
            alu_inputB = immt  # immediate value
        result, zero_flag, self.overflow = self.alu.execute(alu_inputA, alu_inputB, get_bits(immt, 0, 5), EX_signals["alu_op"])
        # print(f"ALU result: {result},alu_inputA: {alu_inputA}, alu_inputB: {alu_inputB},FW_A: {FW_A},FW_B: {FW_B}, zero_flag: {zero_flag}")
        # print(control_signals["reg_dst"])
        if EX_signals["reg_dst"]:
            regd = rd_index
        else:
            regd = rt_index
        if self.overflow and EX_CODE== 0x00:
            print("Overflow occurred. Result not written to register.")
            WB_signals["reg_write"] = 0
            MEM_signals["mem_write"] = 0
            self.overflow = 0  # Reset overflow flag after handling
            EX_CODE = 0x0C
        return {
            "EXL": id_info["EXL"],
            "UM": id_info["UM"],
            "EX_CODE": EX_CODE,
            "EPC": id_info["EPC"],
            "WB_signals":WB_signals,
            "MEM_signals":MEM_signals,
            "result":result,
            "zero_flag":zero_flag,
            "rData2":rData2,
            "regd":regd,
            "pc":pc,
        }
    def MEM(self, ex_info):
        EXL = ex_info["EXL"]
        UM = ex_info["UM"]
        EX_CODE = ex_info["EX_CODE"]
        EPC = ex_info["EPC"]
        WB_signals = ex_info["WB_signals"]
        MEM_signals = ex_info["MEM_signals"]
        result = ex_info["result"]
        zero_flag = ex_info["zero_flag"]
        rData2 = ex_info["rData2"]
        regd = ex_info["regd"]
        pc = ex_info["pc"]

        self.Forward_EX_MEM_data = result
        self.Forwarding_unit.ex_mem_RegWrite = WB_signals["reg_write"]
        self.Forwarding_unit.ex_mem_RegDst = regd

        rMData = 0
        Error_CODE = 0x00
        if MEM_signals["mem_read"]==1 or MEM_signals["mem_write"]==1:
            rMData , Error_CODE= self.Data_Memory(result, rData2, MEM_signals["mem_read"], MEM_signals["mem_write"],EXL, UM)
            
        if Error_CODE!=0:
            WB_signals["reg_write"] = 0
            EX_CODE = Error_CODE

        # ExL handle
        if EX_CODE!=0x00:
            #TODO : EPC adjust depends on stageEXP
            self.cp0.write_register(self.cp0.name_map['Cause'], EX_CODE<<2)
            if EX_CODE == 0x08:
                self.cp0.write_register(self.cp0.name_map['EPC'], EPC+4)
            else:
                self.cp0.write_register(self.cp0.name_map['EPC'], EPC)
            self.cp0.to_exception_mode() 
            self.PCSrc_Exception = 1
            self.IF_ID.flush()
            self.ID_EX.flush()
            self.EX_MEM.flush()
        
        return {
            "WB_signals":WB_signals,
            "rMData":rMData,
            "result":result,
            "regd":regd,
        }
    def WB(self, mem_info):
        WB_signals = mem_info["WB_signals"]
        rMData = mem_info["rMData"]
        result = mem_info["result"]
        regd = mem_info["regd"]
        
        self.Forwarding_unit.mem_wb_RegWrite = WB_signals["reg_write"]
        self.Forwarding_unit.mem_wb_RegDst = regd

        if WB_signals["mem_to_reg"]:
            print(f"Memory read: {bin(rMData)} from address {hex(result)}")
            result = rMData

        # print(f"Writing to register index {regd} with value {result}")
        if WB_signals["reg_write"]:
            self.registers.write_register(regd, result)

        self.Forward_MEM_WB_data = result

    def execute(self):
        # ===WB===
        self.WB(self.MEM_WB.read())
        # ===MEM===
        mem_result = self.MEM(self.EX_MEM.read())
        self.MEM_WB.write(mem_result)
        # ===EX===
        ex_result = self.EX(self.ID_EX.read())
        self.EX_MEM.write(ex_result)
        # ===ID===
        id_result = self.ID(self.IF_ID.read())
        self.ID_EX.write(id_result)
        # ===IF===
        if_result = self.IF()
        self.IF_ID.write(if_result)

        self.IF_ID.tick()
        self.ID_EX.tick()
        self.EX_MEM.tick()
        self.MEM_WB.tick()

                



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
            "sign_ext": 0,
            "alu_op": 0,
            "jump": 0
        }
        op = []
        for i in range(6):
            op.append(opcode & (1<<5-i))
        r_type, lw, sw, beq, addi,lui = 0,0,0,0,0,0
        r_type = (not op[5]) and (not op[4]) and (not op[3]) and (not op[2]) and (not op[1]) and (not op[0]) #000000
        lw = op[5] and op[4] and (not op[3]) and (not op[2]) and (not op[1]) and op[0] #100011
        sw = op[5] and op[4] and (not op[3]) and op[2] and (not op[1]) and op[0] #101011
        beq = (not op[5]) and (not op[4]) and op[3] and (not op[2]) and (not op[1]) and (not op[0]) #000100
        j = (not op[5]) and op[4] and (not op[3]) and (not op[2]) and (not op[1]) and (not op[0]) #000010
        lui = op[5] and  op[4] and  op[3] and op[2] and (not op[1]) and (not op[0]) #001111
        addi = (not op[5]) and (not op[4]) and (not op[3]) and op[2] and (not op[1]) and (not op[0]) #00100
        ori = op[5] and (not op[4]) and op[3] and op[2] and (not op[1]) and (not op[0]) #001101
        # r_type = bool(r_type)
        # lw = bool(lw)
        # sw = bool(sw)
        # beq = bool(beq)
        signals["reg_dst"] = r_type
        signals["alu_src"] = (lw or sw or addi or lui or ori)
        signals["mem_to_reg"] = lw
        signals["reg_write"] = (r_type or lw or addi or lui or ori)
        signals["mem_read"] = lw
        signals["mem_write"] = sw
        signals["branch"] = beq
        signals["jump"] = j
        signals["sign_ext"] = lw or sw or beq or addi
        
        for key,value in signals.items():
            signals[key] = 1 if value else 0 # Formatting for clear looks <3
        alu_3bits = 0
        if r_type:
            alu_3bits |= 0b010
        elif beq:
            alu_3bits |= 0b001
        elif lui:
            alu_3bits |= 0b011
        elif ori:
            alu_3bits |= 0b100
        signals["alu_op"] = alu_3bits

        # print(f"op: {op}")
        # print(f"r_type: {r_type}, lw: {lw}, sw: {sw}, beq: {beq}")
        # print(f"control_unit: {signals}")
        return signals
    def Data_Memory(self, address, write_data, mem_read, mem_write, EXL, UM):
        is_Kernal = (not UM) or EXL
        if not is_Kernal and get_bits(address, 31, 31) == 1:
            print(f"Address Error on Load/Store: {hex(address)} is out of range") #0x04 AdEL illegal memory access
            return 0 , 0x04
        if address & 0x00000003 != 0:
            print(f"Address Error on Load/Store: {hex(address)} must be word-aligned") #0x05 AdES misaligned memory
            return 0 , 0x05

        if mem_read:
            return self.memory.read(address) ,0
        if mem_write:
            self.memory.write(address, write_data)
            return 0 ,0
class CPUCore:
    def __init__(self):
        self.registers = Registers()
        self.alu = ALU()
        self.cp0 = CP0()
        self.pc = 0x00400000 #Program_Counter
        self.memory = Memory()
        
        self.overflow = 0
        self.memError = 0
        
        self.exception = None
        self.EV_ADDRESS = 0x80000180 # Exception Vector Address
        self.cp0.to_user_mode()

    def execute(self):
        # ===IF===
        bin_code = self.Instruction_MEM(self.pc)
        EXL = get_bits(self.cp0.read_register(self.cp0.name_map['Status']), 1, 1)
        UM = get_bits(self.cp0.read_register(self.cp0.name_map['Status']), 4, 4)
        EX_CODE = get_bits(self.cp0.read_register(self.cp0.name_map['Cause']), 2, 6)
        pc = self.pc + 4
        print(f"PC: {hex(self.pc)}, Instruction: {bin_code:032b}, EXL: {EXL}, UM: {UM}, EX_CODE: {EX_CODE}")
        # print(f"EXL: {EXL}, UM: {UM}, EX_CODE: {EX_CODE}")
        # ===ID===
        # print(f"Executing instruction: {bin_code:032b}")
        jAddress = get_bits(bin_code, 0, 25)
        jAddress = jAddress << 2
        jAddress = (get_bits(self.pc, 28, 31) << 28) | jAddress

        # print(f"get_bits(bin_code, 0, 5): {get_bits(bin_code, 26, 31):06b}")
        control_signals = self.control_unit(get_bits(bin_code, 26, 31))
        # print(f"Control signals: {control_signals}")
        if get_bits(bin_code, 26, 31) == 0 and get_bits(bin_code, 0, 5) == 0b001100:
            # print(f"Syscall detected")
            # display = self.registers.dump()
            # for i in range(0, len(display), 4):
            #     print(" ".join(f"{k}: {hex(v)}" for k, v in list(display.items())[i:i+4]))
            EXL = 1
            EX_CODE = 0x08
            control_signals["reg_write"] = 0
            control_signals["mem_write"] = 0
            print(f"EXL: {EXL}, EX_CODE: {EX_CODE}, pc: {hex(pc)}")
        rData1 = self.registers.read_register(get_bits(bin_code, 21, 25))
        rData2 = self.registers.read_register(get_bits(bin_code, 16, 20))
        rd_index = get_bits(bin_code, 11, 15)
        # print(f"rs({get_bits(bin_code, 21, 25)}): {rData1}, rt({get_bits(bin_code, 16, 20)}): {rData2}")

        immt = get_bits(bin_code, 0, 15)
        sign_bit = (immt >> 15) & 1
        if control_signals["sign_ext"]:
            if sign_bit == 1:
                immt |= 0xFFFF0000 #sign extend
            else:
                immt &= 0x0000FFFF #zero extend
        # print(f"imm: {immt}")
        # ===EX===

        branch_address = immt << 2
        branch_address = (pc + branch_address)& 0xFFFFFFFF

        alu_input = rData2
        # print(control_signals["alu_src"])
        if control_signals["alu_src"]:  #alu_src multiplexor
            alu_input = immt  # immediate value
            # print(f"ALUSrc is 1, using constant {op_b} as op_b")
        # print(f"rData1: {rData1}, rData2: {rData2},alu_input: {alu_input}, opcode: {get_bits(bin_code, 0, 5)}, control_signals: {control_signals}")
        result, zero_flag, self.overflow = self.alu.execute(rData1, alu_input, get_bits(immt, 0, 5), control_signals["alu_op"])
        # print(f"ALU result: {result}, zero_flag: {zero_flag}")

        # ===MEM===
        if self.overflow:
            print("Overflow occurred. Result not written to register.")
            control_signals["reg_write"] = 0
            control_signals["mem_write"] = 0
            self.overflow = 0  # Reset overflow flag after handling
            EX_CODE = 0x0C
            EXL = 1

        if control_signals["branch"] and zero_flag:
            pc = branch_address
            # print(f"Branch taken to address {hex(pc)}, originally {hex(self.pc)}")
        rMData = 0
        if control_signals["jump"]:
            pc = jAddress
        if control_signals["mem_read"]==1 or control_signals["mem_write"]==1:
            rMData , self.memError, EX_CODE= self.Data_Memory(result, rData2, control_signals["mem_read"], control_signals["mem_write"],EXL, UM)
        if self.memError:
            control_signals["reg_write"] = 0
            EXL = 1

        if control_signals["mem_to_reg"]:
            print(f"Memory read: {bin(rMData)} from address {hex(result)}")
            result = rMData
        # ===WB===
        if self.exception:
            print(f"Exception: {self.exception}")
            control_signals["reg_write"] = 0
            control_signals["mem_write"] = 0
            EXL = 1
        

        # print(control_signals["reg_dst"])
        if control_signals["reg_dst"]:
            regd = rd_index
        else:
            regd = get_bits(bin_code, 16, 20)
        # print(f"Writing to register index {regd} with value {result}")
        if control_signals["reg_write"]:
            self.registers.write_register(regd, result)
        self.cp0.write_register(self.cp0.name_map['Cause'], EX_CODE<<2) 
        if EXL:
            pc = self.EV_ADDRESS
            self.cp0.write_register(self.cp0.name_map['EPC'], self.pc+4)
            self.cp0.to_exception_mode()
        
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
            "sign_ext": 0,
            "alu_op": 0,
            "jump": 0
        }
        op = []
        for i in range(6):
            op.append(opcode & (1<<5-i))
        r_type, lw, sw, beq, addi,lui = 0,0,0,0,0,0
        r_type = (not op[5]) and (not op[4]) and (not op[3]) and (not op[2]) and (not op[1]) and (not op[0]) #000000
        lw = op[5] and op[4] and (not op[3]) and (not op[2]) and (not op[1]) and op[0] #100011
        sw = op[5] and op[4] and (not op[3]) and op[2] and (not op[1]) and op[0] #101011
        beq = (not op[5]) and (not op[4]) and op[3] and (not op[2]) and (not op[1]) and (not op[0]) #000100
        j = (not op[5]) and op[4] and (not op[3]) and (not op[2]) and (not op[1]) and (not op[0]) #000010
        lui = op[5] and  op[4] and  op[3] and op[2] and (not op[1]) and (not op[0]) #001111
        addi = (not op[5]) and (not op[4]) and (not op[3]) and op[2] and (not op[1]) and (not op[0]) #00100
        ori = op[5] and (not op[4]) and op[3] and op[2] and (not op[1]) and (not op[0]) #001101
        # r_type = bool(r_type)
        # lw = bool(lw)
        # sw = bool(sw)
        # beq = bool(beq)
        signals["reg_dst"] = r_type
        signals["alu_src"] = (lw or sw or addi or lui or ori)
        signals["mem_to_reg"] = lw
        signals["reg_write"] = (r_type or lw or addi or lui or ori)
        signals["mem_read"] = lw
        signals["mem_write"] = sw
        signals["branch"] = beq
        signals["jump"] = j
        signals["sign_ext"] = lw or sw or beq or addi
        
        for key,value in signals.items():
            signals[key] = 1 if value else 0 # Formatting for clear looks <3
        alu_3bits = 0
        if r_type:
            alu_3bits |= 0b010
        elif beq:
            alu_3bits |= 0b001
        elif lui:
            alu_3bits |= 0b011
        elif ori:
            alu_3bits |= 0b100
        signals["alu_op"] = alu_3bits

        # print(f"op: {op}")
        # print(f"r_type: {r_type}, lw: {lw}, sw: {sw}, beq: {beq}")
        # print(f"control_unit: {signals}")
        return signals
    def Data_Memory(self, address, write_data, mem_read, mem_write, EXL, UM):
        is_Kernal = (not UM) or EXL
        if not is_Kernal and get_bits(address, 31, 31) == 1:
            print(f"Address Error on Load/Store: {hex(address)} is out of range") #0x04 AdEL illegal memory access
            return 0 ,1, 0x04
        if address & 0x00000003 != 0:
            print(f"Address Error on Load/Store: {hex(address)} must be word-aligned") #0x05 AdES misaligned memory
            return 0 ,1, 0x05

        if mem_read:
            return self.memory.read(address) ,0, 0
        if mem_write:
            self.memory.write(address, write_data)
            return 0 ,0, 0
class ALU:
    def __init__(self):
        self.exception = None
        self.overflow = 0
    def execute(self,rData1, rData2, func_code,alu_op):
        ALU_control_signals = self.ALU_control_unit(func_code, alu_op)
        # print(f"ALU control signals: {ALU_control_signals}")
        alu_result, zero_flag, overflow = self.ALU_32(ALU_control_signals, rData1, rData2)

        if alu_op == 0b011:  # LUI operation
            alu_result = (rData2 << 16) & 0xFFFFFFFF

        return alu_result, zero_flag, overflow
    def ALU_control_unit(self, func_code,alu_op):

        # print(f"ALU_control_unit: func_code={func_code}, alu_op = {alu_op}")
        signals = [0] * 4 # [ainvert,binvert, op1, op0]
        match alu_op,func_code:
            case 0b010, 0b100100: pass #and
            case 0b010, 0b100101: signals[3] = 1 #or
            case 0b010, 0b100000: signals[2] = 1 #add
            case 0b010, 0b100010: signals[1] = 1; signals[2] = 1 #sub
            case 0b010, 0b100111: signals[0] = 1; signals[1] = 1 #nor
            case 0b010, 0b101010: signals[1] = 1; signals[2] = 1; signals[3] = 1 #slt
            
            case 0b000,_: signals[2] = 1 #lw, sw, addi(add)
            case 0b001,_: signals[1] = 1; signals[2] = 1 #beq(sub)
            case 0b100,_: signals[3] = 1 #ori
            case _: pass
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
        self.label_table = {}
        self.reg_table = registers
        self.exception = None
        self.errors = []
        self.virtual_address = 0x00400000
        self.nop = 0
        self.inst_map = {
            'add':  (0b000000, 0b100000, 'R'),
            'sub':  (0b000000, 0b100010, 'R'),
            'and':  (0b000000, 0b100100, 'R'),
            'or':   (0b000000, 0b100101, 'R'),
            'nor':  (0b000000, 0b100111, 'R'),
            'slt':  (0b000000, 0b101010, 'R'),
            'sll':  (0b000000, 0b000000, 'R'),
            'syscall': (0b000000, 0b001100, 'R'),

            'addi': (0b001000, 0b000000, 'I'),
            'lw':   (0b100011, 0b000000, 'I'),
            'sw':   (0b101011, 0b000000, 'I'),
            'beq':  (0b000100, 0b000000, 'I'),
            'lui':  (0b001111, 0b000000, 'I'),
            'ori':  (0b001101, 0b000000, 'I'),

            'j':    (0b000010, 0b000000, 'J'),
        }
    def compile_r_type(self, cmd,bin_code,func_code): #R-type[inst rd rs rt/shamt]
        if len(cmd) < 4:
            if cmd[0] == 'syscall':
                return 0x0000000C # SYSCALL
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
    def compile_i_type(self, cmd,bin_code,offset): #I-type[inst rt rs imm]
        if cmd[2].find("(") != -1 and cmd[2].find(")") != -1: #lw/sw format: lw $t0, 4($t1)
            cmd.insert(3, cmd[2].split("(")[0])
            cmd[2] = cmd[2].split("(")[1].split(")")[0]
        if cmd[0].lower() == "lui":
            cmd.insert(2, "zero")
        print(f"cmd after parsing: {cmd}")

        if len(cmd) < 4:
            self.exception = "Invalid I-type instruction format: Not enough arguments"
            bin_code = self.nop
            return bin_code

        rt,rs,imm = 0,0,0
        try:
            rt = self.reg_table.name_map[cmd[1]]&0x1F
            rs = self.reg_table.name_map[cmd[2]]&0x1F # op:6, rs:5, rt:5, imm:16
            # print(f"rs: {rs}, rt: {rt}, imm_str: {cmd[3]}")
            if cmd[0].lower() == "beq":
                rs,rt = rt,rs
                try:
                    print(self.label_table)
                    imm = self.label_table[cmd[3]][1] - (offset + 1) # label offset
                    print(f"Label '{cmd[3]}' found in label_table. Using offset {imm}.")
                except KeyError:
                    print(f"Label '{cmd[3]}' not found in label_table. Attempting to parse as an immediate value.")
                    imm = int(cmd[3], 0) & 0xFFFF
            else:
                imm = int(cmd[3],0) & 0xFFFF
        except KeyError:
            self.exception = "Invalid I-type instruction format: Invalid register name"
            bin_code = self.nop
            return bin_code
        except ValueError:
            self.exception = "Invalid I-type instruction format: Invalid immediate value"
            bin_code = self.nop
            return bin_code
        bin_code |= rs << 21
        bin_code |= rt << 16
        bin_code |= imm&0xFFFF
        # print(f"rs: {rs << 21}, rt: {rt}, imm: {imm}")
        # print(f"bin_code after I-type: {bin_code:032b}")
        return bin_code
    def compile_j_type(self, cmd,bin_code): #J-type[inst address]
        if len(cmd) < 2:
            self.exception = "Invalid J-type instruction format"
            bin_code = self.nop
            return bin_code
        try:
            address = self.label_table[cmd[1]][0]
        except KeyError:
            try:
                print(f"Label '{cmd[1]}' not found in label_table. Attempting to parse as an address.")
                address = int(cmd[1],0)
            except ValueError:
                self.exception = "Invalid J-type instruction format: Invalid address"
                bin_code = self.nop
                return bin_code
        address = get_bits(address, 2, 27)
        bin_code |= address
        return bin_code
    def compile(self, cmd,offset):
        cmd = cmd.split("#")[0]  # Remove comments
        cmd = cmd.replace("$", "").replace(",", " ").replace("\t", " ").strip().split()
        if not cmd:
            # self.exception = "Empty command"
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
            self.exception = "Invalid instruction(unsupported or undefined instruction)"
            bin_code = self.nop
            return bin_code
        bin_code |= opcode << WIDTH - 6
        # print(f"bin_code after opcode: {bin_code:032b}")
        # print(f"Opcode: {opcode:06b}, Function code: {func_code:06b}, Instruction type: {inst_type}")
        match  inst_type:
            case 'R': 
                bin_code = self.compile_r_type(cmd, bin_code,func_code)
            case 'I':
                bin_code = self.compile_i_type(cmd, bin_code,offset)
            case 'J':
                bin_code = self.compile_j_type(cmd, bin_code)
            case _:
                self.exception = "Invalid instruction type"
                bin_code = self.nop
        return bin_code

    def label_mapping(self,label,label_table,offset):
        if not label:
            return label_table
        if not label or label in label_table:
            self.exception = f"Invalid label: Label '{label}' is empty or already exists"
            return label_table
        label_table[label] = offset * 4 + self.virtual_address,offset
        print(f"Label '{label}' mapped to address {hex(label_table[label][0])} and offset {label_table[label][1]}.")
        return label_table

    def run(self, code):
        process_code = []
        program = []
        self.label_table = {}
        offset = 0
        label = ""
        for i in range(0, len(code.splitlines())):
            line = code.splitlines()[i]
            if line.strip() == "":
                continue
            offset += 1
            line = line.split("#")[0]  # Remove comments
            line = line.replace("$", "").replace(",", " ").replace("\t", " ").strip()
            print(f"Compiling instruction {i}: {line}")
            label = line.split(":")[0] if ":" in line else ""
            line = line.split(":")[1].strip() if ":" in line else line
            if line.strip() == "":
                offset -= 1
            if label:
                self.label_table = self.label_mapping(label,self.label_table,offset)
                if self.exception:
                    self.errors.append(self.exception+f" at instruction '{code.splitlines()[i]}' on line {offset+2}")
                    self.exception = None
            if line.strip() != "":
                process_code.append(line)
        offset = 0
        for line in process_code:
            bin_code = 0
            bin_code = self.compile(line,offset)
            program.append(bin_code)
            if self.exception:
                self.exception+= f" at instruction '{line}' on line {offset+1}"
                self.errors.append(self.exception)
                self.exception = None
            offset += 1
        # print(f"Processed code: {process_code}")
       

        return program
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
        self.memory.write(address+4, 0b00100000000000100000000000001010) #addi $v0, $zero, 10
        self.memory.write(address+8, 0x0000000C) #syscall

class SimpleOS:
    def __init__(self, CPU):
        self.CPU = CPU
        self.cause_map = {
            0x04: "Address error (load)",
            0x05: "Address error (store)",
            0x08: "Syscall",
            0x0C: "Overflow",
        }
    def run(self):
        i =0
        while i<100:
            i+=1
            self.CPU.execute()
            if self.CPU.pc == self.CPU.EV_ADDRESS:
                if self.exception_handler():
                    continue
                else:
                    break
    def exception_handler(self):
        Cause = self.CPU.cp0.read_register(self.CPU.cp0.name_map['Cause'])
        Status = self.CPU.cp0.read_register(self.CPU.cp0.name_map['Status'])

        print(f"Cause: {Cause:032b}")
        print(f"Status: {Status:032b}")
        EX_CODE = (Cause >> 2) & 0x1F
        print(f"Exception Code: {hex(EX_CODE)}")
        print(f"Exception Type: {self.cause_map.get(EX_CODE, 'Unknown')}")
        match EX_CODE:
            case 0x08:
                return self.syscall_handler()
        return 0
    def syscall_handler(self):
        v0 = self.CPU.registers.read_register(self.CPU.registers.name_map['v0'])
        print(f"Syscall code: {v0}")
        match v0:
            case 0: # do nothing for testing only
                print("Syscall: No operation(testing only)")
            case 1:  # print integer
                a0 = self.CPU.registers.read_register(self.CPU.registers.name_map['a0'])
                print(f"Syscall: Print Integer: {a0}")
            case 4:  # print string
                a0 = self.CPU.registers.read_register(self.CPU.registers.name_map['a0'])
                string = ""
                while True:
                    char_code = self.CPU.memory.read_byte(a0)
                    # print(f"Reading char code {char_code} from address {hex(a0)}")
                    if char_code == 0:
                        break
                    string += chr(char_code)
                    # print(f"Current string: {string}")
                    a0 += 1
                print(f"Syscall: Print String: {string}")
            case 10:  # exit
                print("Syscall: Exit")
                self.CPU.pc = self.CPU.cp0.read_register(self.CPU.cp0.name_map['EPC'])
                self.CPU.cp0.eret()
                return 0
            case _:
                print(f"Syscall: Unknown syscall code {v0}")
                return 0
        self.CPU.pc = self.CPU.cp0.read_register(self.CPU.cp0.name_map['EPC'])
        self.CPU.cp0.eret()
        return 1
def interface():
    # CPU = CPUCore()
    CPU = Pipelined_CPUCore()
    registers = CPU.registers
    compiler_32 = Compiler(registers)
    loader = Loader(CPU)
    OS = SimpleOS(CPU)
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
addi $t0, $zero, -32768   # $t0 = 0xFFFF8000
lw   $t1, 0($t0)          # user mode exception(AdEL)
"""
    code = """
addi $t0, $zero, 32767
jump_label:
add  $t0, $t0, $t0
j jump_label
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
    code = """
syscall
syscall
syscall
addi $t0, $zero, 5
addi $t1, $zero, 5
beq  $t0, $t1, 2     # should jump to 999 if $t0 == $t1
addi $t2, $zero, 111   # this instruction should be skipped if branch is taken
syscall
addi $t2, $zero, 999   # this instruction should be executed if branch is taken
"""

    code = """
addi $t0, $zero, 5
addi $t1, $zero, 5
addi $t2, $zero, 0
addi $t3, $zero, 1
loop:
add $t2, $t2, $t1
sub $t0, $t0, $t3
beq $t0, $zero, end_loop
j loop
addi $t4, $zero, 999
end_loop:

"""

#     code = """
# addi $t0, $zero, 10
# addi $a0, $zero, 1
# addi $t1, $zero, 0
# addi $t2, $zero, 1
# loop:
#     add $t3, $t1, $t2
#     add  $t1, $zero, $t2
#     add $t2, $zero, $t3
#     sub $t0, $t0, $a0
#     slt $t3, $t0, $zero
#     beq  $t3, $zero, loop
# """
    code = """
addi $t0, $zero, 46
addi $t0, $t0, -2
addi $t1, $zero, 0
sw $t1, 0($sp)
addi $t1, $zero, 1
addi $sp, $sp, -4
sw $t1, 0($sp)
Loop:
lw $t1, 4($sp)
lw $t2, 0($sp)
add $t3, $t1, $t2
addi $sp, $sp, -4
sw $t3, 0($sp)
addi $t0, $t0, -1
slt $t4, $t0, $zero
beq $t4, $zero, Loop
add $a0, $zero, $sp
addi $v0, $zero, 1
syscall
"""

    code = """
addi $sp, $sp, -8
lui $t0,0
ori $t0, $t0, 0x3233
sw $t0, 4($sp)
lui $t0, 0x5350
ori $t0, $t0, 0x494D
sw $t0, 0($sp)
add $a0, $zero, $sp
addi $v0, $zero, 4
syscall
"""
#     code = """
# beq $zero, $zero, label
# addi $s0, $zero, 5
# addi $s2, $zero, 5
# addi $s3, $zero, 5

# label:
# addi $s1, $zero, 5
# sll $zero, $zero, 0

# """
#     code = """
# addi $s1, $zero, 1
# add $s1, $s1, $s1
# add $s1, $s1, $s1
# add $s1, $s1, $s1
# syscall
# add $s1, $s1, $s1
# """

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
                
                print(" ".join(f"{k}: {hex(v)}" for k, v in list(display.items())[i:i+4]))
            continue
        if cmd == "memory" or cmd == "mem":
            display = CPU.memory.dump()
            for i in range(0, len(display), 4):
                print(" ".join(f"{k}: {hex(v)}" for k, v in list(display.items())[i:i+4]))
            continue
        program = compiler_32.run(code)
        if compiler_32.errors:
            for error in compiler_32.errors:
                print(f"Error: {error}")
            compiler_32.errors = []
            continue
        loader.load_program(program)
        OS.run()




if __name__ == "__main__":
        interface()