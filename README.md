# MIPS_CPU_Simulator_PoC
A MIPS32 CPU Simulator implemented in Python. This project simulates the core hardware components and data path of a MIPS processor, designed as a proof-of-concept (PoC) while self-studying computer architecture fundamentals.

## Goal
- Approaching hardware-level MIPS32 architecture
- Implement basic Loader and Compiler/Assembler and Exception Handling concepts.
- Practice Object-Oriented Programming (OOP) in hardware design.

## Supported Instructions
### R-Type Instructions
- `add`/`sub` 
- `and`/`or`/`nor`
- `slt`
- `syscall`(exit only)

### I-Type Instructions
- `addi`/`ori`/`lui`
- `lw`/`sw`/`beq`(label support!)

### J-Type Instructions
- `j`(label support!)

## Requirement
- Python 3.x

## How to Run
Clone the repository and run the main script. The program includes an interactive CLI and a hardcoded demo.
```bash
python main.py
```
*(Feel free to modify the `code` string inside `main.py` to test your own assembly programs!)*

### Example (Fibonacci Sequence)
The default demo runs the following MIPS assembly to calculate the Fibonacci sequence and store it in memory:
```assembly
addi $s0, $zero, 1     # F(1) = 1
addi $s1, $zero, 1     # F(2) = 1
addi $sp, $zero, 100   # push stack pointer to 100
sw   $s0, 0($sp)       # Memory[100] = 1
sw   $s1, 4($sp)       # Memory[104] = 1
add  $s2, $s0, $s1     # F(3) = 1 + 1 = 2
sw   $s2, 8($sp)       # Memory[108] = 2
```

Type `registers` or `regs` in the CLI after execution to inspect the 32-bit state of all CPU registers.

## To-Do
- remaining Instructions support
- Pipelining implementation