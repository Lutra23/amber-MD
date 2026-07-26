"""
GJF 文件验证工具
检查电荷和自旋多重度的合理性
"""
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# 完整的元素原子序数列表
ATOMIC_NUMBERS: Dict[str, int] = {
    'H': 1, 'He': 2, 'Li': 3, 'Be': 4, 'B': 5, 'C': 6, 'N': 7, 'O': 8, 'F': 9, 'Ne': 10,
    'Na': 11, 'Mg': 12, 'Al': 13, 'Si': 14, 'P': 15, 'S': 16, 'Cl': 17, 'Ar': 18,
    'K': 19, 'Ca': 20, 'Sc': 21, 'Ti': 22, 'V': 23, 'Cr': 24, 'Mn': 25, 'Fe': 26, 
    'Co': 27, 'Ni': 28, 'Cu': 29, 'Zn': 30, 'Ga': 31, 'Ge': 32, 'As': 33, 'Se': 34, 
    'Br': 35, 'Kr': 36, 'Rb': 37, 'Sr': 38, 'Y': 39, 'Zr': 40, 'Nb': 41, 'Mo': 42, 
    'Tc': 43, 'Ru': 44, 'Rh': 45, 'Pd': 46, 'Ag': 47, 'Cd': 48, 'In': 49, 'Sn': 50, 
    'Sb': 51, 'Te': 52, 'I': 53, 'Xe': 54, 'Cs': 55, 'Ba': 56, 'La': 57, 'Ce': 58, 
    'Pr': 59, 'Nd': 60, 'Pm': 61, 'Sm': 62, 'Eu': 63, 'Gd': 64, 'Tb': 65, 'Dy': 66, 
    'Ho': 67, 'Er': 68, 'Tm': 69, 'Yb': 70, 'Lu': 71, 'Hf': 72, 'Ta': 73, 'W': 74, 
    'Re': 75, 'Os': 76, 'Ir': 77, 'Pt': 78, 'Au': 79, 'Hg': 80, 'Tl': 81, 'Pb': 82, 
    'Bi': 83, 'Po': 84, 'At': 85, 'Rn': 86, 'Fr': 87, 'Ra': 88, 'Ac': 89, 'Th': 90, 
    'Pa': 91, 'U': 92, 'Np': 93, 'Pu': 94, 'Am': 95, 'Cm': 96, 'Bk': 97, 'Cf': 98, 
    'Es': 99, 'Fm': 100, 'Md': 101, 'No': 102, 'Lr': 103, 'Rf': 104, 'Db': 105, 
    'Sg': 106, 'Bh': 107, 'Hs': 108, 'Mt': 109, 'Ds': 110, 'Rg': 111, 'Cn': 112, 
    'Nh': 113, 'Fl': 114, 'Mc': 115, 'Lv': 116, 'Ts': 117, 'Og': 118
}


class GJFValidator:
    """GJF 文件验证器"""
    
    def __init__(self, filepath: str):
        """
        初始化验证器
        
        参数:
            filepath: GJF 文件路径
        """
        self.filepath = Path(filepath)
        self.charge: Optional[int] = None
        self.spin: Optional[int] = None
        self.atoms: List[Tuple[str, float, float, float]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def read_gjf(self) -> bool:
        """
        读取 GJF 文件内容
        
        返回:
            读取成功返回 True，失败返回 False
        """
        try:
            with self.filepath.open('r', encoding='utf-8') as file:
                lines = file.readlines()
            
            charge_spin_line_found = False
            for line in lines:
                line = line.strip()
                
                # 跳过注释行和空行
                if line.startswith('#') or not line:
                    continue
                
                # 查找电荷和自旋多重度行
                if not charge_spin_line_found:
                    if re.match(r'^\s*-?\d+\s+\d+\s*$', line):
                        parts = line.split()
                        self.charge = int(parts[0])
                        self.spin = int(parts[1])
                        charge_spin_line_found = True
                        continue
                
                # 解析原子坐标
                atom_data = line.split()
                if len(atom_data) >= 4:
                    try:
                        element = atom_data[0]
                        coords = tuple(map(float, atom_data[1:4]))
                        self.atoms.append((element, *coords))
                    except ValueError:
                        self.warnings.append(f"无法解析坐标行：{line}")
            
            if not charge_spin_line_found:
                self.errors.append("未找到电荷和自旋多重度行")
                return False
            
            return True
            
        except FileNotFoundError:
            self.errors.append(f"文件不存在：{self.filepath}")
            return False
        except Exception as e:
            self.errors.append(f"读取文件失败：{e}")
            return False
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证 GJF 文件的合理性
        
        返回:
            (是否有效，错误信息列表)
        """
        if self.charge is None or self.spin is None:
            return False, ["未找到电荷和自旋多重度"]
        
        if not self.atoms:
            return False, ["未找到原子坐标"]
        
        # 计算电子总数
        electron_count = 0
        for atom in self.atoms:
            element = atom[0]
            if element not in ATOMIC_NUMBERS:
                return False, [f"未知元素：{element}"]
            electron_count += ATOMIC_NUMBERS[element]
        
        # 考虑电荷调整电子数
        electron_count -= self.charge
        
        # 计算预期的自旋多重度
        # 单重态：所有电子成对，自旋=1
        # 双重态：一个未成对电子，自旋=2
        # 三重态：两个未成对电子，自旋=3
        unpaired_electrons = electron_count % 2
        expected_spin = 2 * unpaired_electrons + 1
        
        if self.spin != expected_spin:
            return False, [
                f"不合理的自旋多重度：{self.spin}。"
                f"根据电荷 {self.charge} 和电子数 {electron_count}，"
                f"预期为 {expected_spin}"
            ]
        
        return True, []
    
    def check(self) -> Tuple[bool, List[str], List[str]]:
        """
        完整检查流程
        
        返回:
            (是否有效，错误列表，警告列表)
        """
        if not self.read_gjf():
            return False, self.errors, self.warnings
        
        is_valid, errors = self.validate()
        self.errors.extend(errors)
        
        return is_valid, self.errors, self.warnings


def process_gjf_files(directory: str, 
                      move_files: bool = True,
                      verbose: bool = True) -> Dict[str, int]:
    """
    批量处理文件夹中的 GJF 文件
    
    参数:
        directory: GJF 文件所在文件夹
        move_files: 是否移动文件到子文件夹
        verbose: 是否打印详细信息
        
    返回:
        统计字典
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"指定路径不是文件夹：{directory}")
    
    stats = {'valid': 0, 'invalid': 0, 'errors': 0}
    
    if move_files:
        reasonable_dir = dir_path / 'reasonable'
        unreasonable_dir = dir_path / 'unreasonable'
        reasonable_dir.mkdir(exist_ok=True)
        unreasonable_dir.mkdir(exist_ok=True)
    
    gjf_files = list(dir_path.glob('*.gjf'))
    
    if not gjf_files:
        logger.warning(f"未找到 GJF 文件：{directory}")
        return stats
    
    for gjf_file in gjf_files:
        validator = GJFValidator(str(gjf_file))
        is_valid, errors, warnings = validator.check()
        
        if verbose:
            status = "✓ 合理" if is_valid else "✗ 不合理"
            print(f"{gjf_file.name}: {status}")
            if errors:
                for err in errors:
                    print(f"  错误：{err}")
            if warnings:
                for warn in warnings:
                    print(f"  警告：{warn}")
        
        if is_valid:
            stats['valid'] += 1
            if move_files:
                try:
                    shutil.move(str(gjf_file), reasonable_dir / gjf_file.name)
                except Exception as e:
                    logger.error(f"移动文件失败：{e}")
                    stats['errors'] += 1
        else:
            stats['invalid'] += 1
            if move_files:
                try:
                    shutil.move(str(gjf_file), unreasonable_dir / gjf_file.name)
                except Exception as e:
                    logger.error(f"移动文件失败：{e}")
                    stats['errors'] += 1
    
    return stats


if __name__ == "__main__":
    import sys
    
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python 检测电荷_refactored.py <文件夹路径> [--no-move]")
        print("  --no-move: 只检查不移动文件")
        sys.exit(1)
    
    directory = sys.argv[1]
    move_files = '--no-move' not in sys.argv
    
    try:
        stats = process_gjf_files(directory, move_files=move_files)
        print(f"\n处理完成!")
        print(f"  合理：{stats['valid']} 个文件")
        print(f"  不合理：{stats['invalid']} 个文件")
        if stats['errors'] > 0:
            print(f"  错误：{stats['errors']} 个文件")
    except Exception as e:
        print(f"错误：{e}")
        sys.exit(1)
