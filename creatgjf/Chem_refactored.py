"""
Chemistry Utilities Module
提供分子结构处理和格式转换功能
"""
from rdkit import Chem
from rdkit.Chem import AllChem, rdDetermineBonds
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def xyz_to_mol(xyz_file_path: str) -> Optional[Chem.Mol]:
    """
    从 XYZ 文件读取分子结构
    
    参数:
        xyz_file_path: XYZ 文件路径
        
    返回:
        RDKit Mol 对象，失败返回 None
    """
    try:
        with open(xyz_file_path, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            logger.error(f"XYZ 文件格式错误：{xyz_file_path}")
            return None
        
        # 解析原子坐标
        mol = Chem.RWMol()
        for line in lines[2:]:
            parts = line.split()
            if len(parts) < 4:
                continue
            atom_symbol = parts[0]
            x, y, z = map(float, parts[1:4])
            
            try:
                atom = Chem.Atom(atom_symbol)
                idx = mol.AddAtom(atom)
            except ValueError:
                logger.warning(f"未知元素：{atom_symbol}")
                continue
        
        if mol.GetNumAtoms() == 0:
            logger.error("未找到有效原子")
            return None
        
        # 使用 RDKit 的键确定算法（基于距离）
        try:
            rdDetermineBonds.DetermineBonds(mol)
        except Exception as e:
            logger.warning(f"自动确定化学键失败：{e}，尝试使用距离阈值法")
            # 备用方案：基于距离阈值添加键
            _add_bonds_by_distance(mol, lines[2:])
        
        # 生成三维坐标优化
        AllChem.EmbedMolecule(mol, randomSeed=42)
        AllChem.UFFOptimizeMolecule(mol)
        
        return mol.GetMol()
        
    except FileNotFoundError:
        logger.error(f"文件不存在：{xyz_file_path}")
        return None
    except Exception as e:
        logger.error(f"读取 XYZ 文件失败：{e}")
        return None


def _add_bonds_by_distance(mol: Chem.RWMol, lines: list, threshold: float = 1.8) -> None:
    """
    基于原子间距离添加化学键（备用方案）
    
    参数:
        mol: RWMol 对象
        lines: XYZ 文件的坐标行
        threshold: 成键距离阈值（埃）
    """
    coords = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            coords.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
    
    covalent_radii = {
        'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'F': 0.57,
        'P': 1.07, 'S': 1.05, 'Cl': 1.02, 'Br': 1.20, 'I': 1.39,
        'B': 0.84, 'Si': 1.11, 'Na': 1.54, 'Mg': 1.39, 'Al': 1.21,
    }
    
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            elem_i, x_i, y_i, z_i = coords[i]
            elem_j, x_j, y_j, z_j = coords[j]
            
            distance = ((x_i - x_j)**2 + (y_i - y_j)**2 + (z_i - z_j)**2) ** 0.5
            
            radius_i = covalent_radii.get(elem_i, 0.7)
            radius_j = covalent_radii.get(elem_j, 0.7)
            
            if distance < (radius_i + radius_j) * threshold:
                mol.AddBond(i, j, Chem.BondType.SINGLE)


def mol_to_smiles(mol: Chem.Mol) -> Optional[str]:
    """
    将 RDKit Mol 对象转换为 SMILES 字符串
    
    参数:
        mol: RDKit Mol 对象
        
    返回:
        SMILES 字符串，失败返回 None
    """
    if mol is None:
        return None
    
    try:
        # 生成二维坐标以便更好地呈现
        AllChem.Compute2DCoords(mol)
        smiles = Chem.MolToSmiles(mol)
        return smiles
    except Exception as e:
        logger.error(f"生成 SMILES 失败：{e}")
        return None


def xyz_to_smiles(xyz_file_path: str) -> Optional[str]:
    """
    将 XYZ 文件转换为 SMILES 字符串
    
    参数:
        xyz_file_path: XYZ 文件路径
        
    返回:
        SMILES 字符串，失败返回 None
    """
    mol = xyz_to_mol(xyz_file_path)
    return mol_to_smiles(mol)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 示例用法
    import sys
    if len(sys.argv) > 1:
        xyz_path = sys.argv[1]
        smiles = xyz_to_smiles(xyz_path)
        if smiles:
            print(f"Generated SMILES: {smiles}")
        else:
            print("Failed to generate SMILES")
    else:
        print("Usage: python Chem.py <xyz_file>")
