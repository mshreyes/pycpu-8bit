#!/usr/bin/env python3
"""
Standalone 8-Bit CPU Simulator and Two-Pass Assembler.
Supports all 25 opcodes with plain-English step explanations.
"""


class CPU8Bit:
    OPCODES = {
        "NOP": 0x00, "HLT": 0x01, "MOVI": 0x02, "MOV": 0x03,
        "LOAD": 0x04, "STORE": 0x05, "ADD": 0x06, "ADDI": 0x07,
        "SUB": 0x08, "INC": 0x09, "DEC": 0x0A, "AND": 0x0B,
        "OR": 0x0C, "XOR": 0x0D, "CMP": 0x0E, "CMPI": 0x0F,
        "JMP": 0x10, "JZ": 0x11, "JNZ": 0x12, "JC": 0x13,
        "PUSH": 0x14, "POP": 0x15, "CALL": 0x16, "RET": 0x17,
        "OUT": 0x18,
    }
    REV_OPCODES = {v: k for k, v in OPCODES.items()}

    def __init__(self):
        self.ram = [0] * 256
        self.program_backup = [0] * 256
        self.reset()

    def reset(self):
        self.ram = list(self.program_backup)
        self.reg = [0, 0, 0, 0]
        self.pc = 0
        self.sp = 255
        self.ir = 0
        self.mar = 0
        self.mdr = 0
        self.z = 0
        self.c = 0
        self.n = 0
        self.halted = False
        self.stage = "FETCH"
        self.last_stage_run = "IDLE"
        self.cycles = 0
        self.alu_op = "Idle"
        self.decoded_text = "None"
        self.decoded_info = {}
        self.explanation = "Ready. Click 'Small Step' or 'Full Instruction' to begin."
        self.output = []

    def _update_flags(self, raw):
        self.c = 1 if (raw > 255 or raw < 0) else 0
        val = raw & 0xFF
        self.z = 1 if val == 0 else 0
        self.n = 1 if (val & 0x80) != 0 else 0
        return val

    def assemble(self, source_code):
        lines = source_code.splitlines()
        labels, parsed, addr = {}, [], 0
        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.split(";")[0].strip()
            if not line:
                continue
            if line.endswith(":"):
                labels[line[:-1].strip().upper()] = addr
                continue
            if ":" in line:
                lbl, rest = line.split(":", 1)
                labels[lbl.strip().upper()] = addr
                line = rest.strip()
                if not line:
                    continue
            parts = [p.strip() for p in line.replace(",", " ").split() if p.strip()]
            mnem = parts[0].upper()
            if mnem not in self.OPCODES:
                raise ValueError(f"Line {line_num}: Unknown command '{mnem}'")
            parsed.append((line_num, mnem, parts[1:], addr))
            addr += 2

        mem = [0] * 256

        def parse_reg(tok, ln):
            t = tok.upper()
            if t in ("R0", "R1", "R2", "R3"):
                return int(t[1])
            raise ValueError(f"Line {ln}: Expected register R0..R3, got '{tok}'")

        def parse_val(tok, ln):
            t = tok.strip("[]").upper()
            if t in labels:
                return labels[t] & 0xFF
            return int(t, 0) & 0xFF

        for ln, mnem, args, cur_addr in parsed:
            if cur_addr >= 255:
                raise ValueError("Program exceeds 256-byte memory limit.")
            opcode = self.OPCODES[mnem]
            operand = 0
            if mnem in ("INC", "DEC", "PUSH", "POP", "OUT"):
                operand = (parse_reg(args[0], ln) << 6) & 0xFF
            elif mnem in ("MOV", "ADD", "SUB", "AND", "OR", "XOR", "CMP"):
                operand = ((parse_reg(args[0], ln) << 6) | (parse_reg(args[1], ln) << 4)) & 0xFF
            elif mnem in ("MOVI", "ADDI", "CMPI", "LOAD", "STORE"):
                opcode |= (parse_reg(args[0], ln) << 6)
                operand = parse_val(args[1], ln)
            elif mnem in ("JMP", "JZ", "JNZ", "JC", "CALL"):
                operand = parse_val(args[0], ln)
            mem[cur_addr] = opcode & 0xFF
            mem[cur_addr + 1] = operand & 0xFF

        self.program_backup = list(mem)
        self.reset()
        return True

    def step_stage(self):
        if self.halted:
            self.explanation = "CPU is stopped. Click 'Reset' to run again."
            return self.get_state()

        if self.stage == "FETCH":
            self.last_stage_run = "FETCH"
            self.mar = self.pc
            op_byte = self.ram[self.mar]
            arg_byte = self.ram[(self.mar + 1) & 0xFF]
            self.ir = (op_byte << 8) | arg_byte
            old_pc = self.pc
            self.pc = (self.pc + 2) & 0xFF
            self.alu_op = "Idle"
            self.explanation = (
                f"Fetch: Read command from Memory Box #{old_pc} and #{old_pc+1}, "
                f"and moved PC bookmark to Box #{self.pc}."
            )
            self.stage = "DECODE"

        elif self.stage == "DECODE":
            self.last_stage_run = "DECODE"
            op_byte = (self.ir >> 8) & 0xFF
            arg_byte = self.ir & 0xFF
            base_op = op_byte & 0x3F
            rx_hi = (op_byte >> 6) & 0x03
            rx_op = (arg_byte >> 6) & 0x03
            ry_op = (arg_byte >> 4) & 0x03
            mnem = self.REV_OPCODES.get(base_op, "NOP")
            self.decoded_info = {
                "mnem": mnem, "rx_hi": rx_hi, "rx": rx_op, "ry": ry_op, "imm": arg_byte
            }

            if mnem in ("MOVI", "ADDI", "CMPI"):
                self.decoded_text = f"{mnem} R{rx_hi}, {arg_byte}"
            elif mnem in ("LOAD", "STORE"):
                self.decoded_text = f"{mnem} R{rx_hi}, [{arg_byte}]"
            elif mnem in ("MOV", "ADD", "SUB", "AND", "OR", "XOR", "CMP"):
                self.decoded_text = f"{mnem} R{rx_op}, R{ry_op}"
            elif mnem in ("INC", "DEC", "PUSH", "POP", "OUT"):
                self.decoded_text = f"{mnem} R{rx_op}"
            elif mnem in ("JMP", "JZ", "JNZ", "JC", "CALL"):
                self.decoded_text = f"{mnem} Box #{arg_byte}"
            else:
                self.decoded_text = mnem

            self.explanation = (
                f"Decode: Translated the memory numbers into the command '{self.decoded_text}'."
            )
            self.stage = "EXECUTE"

        elif self.stage == "EXECUTE":
            self.last_stage_run = "EXECUTE"
            d = self.decoded_info
            mnem, rx_hi, rx, ry, imm = d["mnem"], d["rx_hi"], d["rx"], d["ry"], d["imm"]
            self.cycles += 1

            if mnem == "NOP":
                self.explanation = "Execute: NOP (Did nothing this step)."
            elif mnem == "HLT":
                self.halted = True
                self.explanation = "Execute: HLT reached. The program is finished."
            elif mnem == "MOVI":
                self.reg[rx_hi] = imm
                self.explanation = f"Execute: Put the number {imm} into Slot R{rx_hi}."
            elif mnem == "MOV":
                self.reg[rx] = self.reg[ry]
                self.explanation = f"Execute: Copied {self.reg[ry]} from Slot R{ry} into Slot R{rx}."
            elif mnem == "LOAD":
                self.mar = imm
                self.reg[rx_hi] = self.ram[imm]
                self.explanation = f"Execute: Read {self.ram[imm]} from Memory Box #{imm} into Slot R{rx_hi}."
            elif mnem == "STORE":
                self.mar = imm
                self.ram[imm] = self.reg[rx_hi]
                self.explanation = f"Execute: Saved {self.reg[rx_hi]} from Slot R{rx_hi} into Memory Box #{imm}."
            elif mnem == "ADD":
                a, b = self.reg[rx], self.reg[ry]
                res = self._update_flags(a + b)
                self.reg[rx] = res
                self.alu_op = f"{a} + {b} = {res}"
                self.explanation = f"Execute: Added R{rx} ({a}) + R{ry} ({b}) = {res}, and saved {res} in R{rx}."
            elif mnem == "ADDI":
                a = self.reg[rx_hi]
                res = self._update_flags(a + imm)
                self.reg[rx_hi] = res
                self.alu_op = f"{a} + {imm} = {res}"
                self.explanation = f"Execute: Added R{rx_hi} ({a}) + {imm} = {res}, and saved {res} in R{rx_hi}."
            elif mnem == "SUB":
                a, b = self.reg[rx], self.reg[ry]
                res = self._update_flags(a - b)
                self.reg[rx] = res
                self.alu_op = f"{a} - {b} = {res}"
                self.explanation = f"Execute: Subtracted R{rx} ({a}) - R{ry} ({b}) = {res}."
            elif mnem == "INC":
                a = self.reg[rx]
                res = self._update_flags(a + 1)
                self.reg[rx] = res
                self.alu_op = f"{a} + 1 = {res}"
                self.explanation = f"Execute: Added 1 to Slot R{rx} ({a} -> {res})."
            elif mnem == "DEC":
                a = self.reg[rx]
                res = self._update_flags(a - 1)
                self.reg[rx] = res
                self.alu_op = f"{a} - 1 = {res}"
                self.explanation = f"Execute: Subtracted 1 from Slot R{rx} ({a} -> {res}). Zero Flag Z is now {self.z}."
            elif mnem in ("AND", "OR", "XOR"):
                a, b = self.reg[rx], self.reg[ry]
                raw = (a & b) if mnem == "AND" else ((a | b) if mnem == "OR" else (a ^ b))
                res = self._update_flags(raw)
                self.reg[rx] = res
                self.alu_op = f"{a} {mnem} {b} = {res}"
                self.explanation = f"Execute: Ran {mnem} on R{rx} ({a}) and R{ry} ({b}) = {res}."
            elif mnem == "CMP":
                a, b = self.reg[rx], self.reg[ry]
                self._update_flags(a - b)
                self.alu_op = f"Compare {a} & {b}"
                self.explanation = f"Execute: Compared R{rx} ({a}) with R{ry} ({b}). Zero Flag Z is {self.z}."
            elif mnem == "CMPI":
                a = self.reg[rx_hi]
                self._update_flags(a - imm)
                self.alu_op = f"Compare {a} & {imm}"
                self.explanation = f"Execute: Compared R{rx_hi} ({a}) with {imm}. Zero Flag Z is {self.z}."
            elif mnem == "JMP":
                self.pc = imm
                self.explanation = f"Execute: Jumped PC bookmark to Memory Box #{imm}."
            elif mnem == "JZ":
                if self.z == 1:
                    self.pc = imm
                    self.explanation = f"Execute: Zero Flag is 1, so jumped PC to Memory Box #{imm}."
                else:
                    self.explanation = "Execute: Zero Flag is 0, so did not jump."
            elif mnem == "JNZ":
                if self.z == 0:
                    self.pc = imm
                    self.explanation = f"Execute: Result was not zero (Z=0), so jumped PC back to Memory Box #{imm}."
                else:
                    self.explanation = "Execute: Result reached zero (Z=1), so loop ended and moved on."
            elif mnem == "JC":
                if self.c == 1:
                    self.pc = imm
                    self.explanation = f"Execute: Carry Flag is 1, so jumped PC to Memory Box #{imm}."
                else:
                    self.explanation = "Execute: Carry Flag is 0, so did not jump."
            elif mnem == "PUSH":
                self.ram[self.sp] = self.reg[rx]
                self.sp = (self.sp - 1) & 0xFF
                self.explanation = f"Execute: Pushed R{rx} ({self.reg[rx]}) onto stack."
            elif mnem == "POP":
                self.sp = (self.sp + 1) & 0xFF
                self.reg[rx] = self.ram[self.sp]
                self.explanation = f"Execute: Popped {self.reg[rx]} from stack into R{rx}."
            elif mnem == "CALL":
                self.ram[self.sp] = self.pc
                self.sp = (self.sp - 1) & 0xFF
                self.pc = imm
                self.explanation = f"Execute: Saved return box on stack and jumped to Box #{imm}."
            elif mnem == "RET":
                self.sp = (self.sp + 1) & 0xFF
                self.pc = self.ram[self.sp]
                self.explanation = f"Execute: Returned from function back to Box #{self.pc}."
            elif mnem == "OUT":
                val = self.reg[rx]
                self.output.append(str(val))
                self.explanation = f"Execute: Printed R{rx}'s value ({val}) to the Screen Output."

            self.stage = "FETCH"
        return self.get_state()

    def step_instruction(self):
        while not self.halted:
            s = self.step_stage()
            if self.last_stage_run == "EXECUTE":
                return s
        return self.get_state()

    def get_state(self):
        return {
            "reg": list(self.reg), "pc": self.pc, "sp": self.sp, "ir": self.ir,
            "mar": self.mar, "z": self.z, "c": self.c, "halted": self.halted,
            "stage": self.stage, "last_stage": self.last_stage_run,
            "cycles": self.cycles, "alu_op": self.alu_op,
            "decoded_text": self.decoded_text, "explanation": self.explanation,
            "output": list(self.output), "ram": list(self.ram)
        }


cpu = CPU8Bit()

if __name__ == "__main__":
    demo = """
    MOVI R0, 14
    MOVI R1, 28
    ADD  R0, R1
    OUT  R0
    HLT
    """
    cpu.assemble(demo)
    while not cpu.halted:
        st = cpu.step_stage()
        print(st["explanation"])
    print("Output:", cpu.output)