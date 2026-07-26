"""
XYZ 到 Gaussian 输入文件 (.gjf) 转换工具
支持批量转换和配置自定义
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class GJFConverter:
    """Gaussian 输入文件转换器"""
    
    DEFAULT_CONFIG = {
        'method': 'B3LYP',
        'basis': '6-31G(d)',
        'job_type': 'Opt',
        'title': 'Molecule',
        'charge': 0,
        'multiplicity': 1,
        'chk_extension': '.chk'
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化转换器
        
        参数:
            config: 配置字典，可选。未提供则使用默认配置
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
    
    def xyz_to_gjf(self, xyz_filepath: str, gjf_filepath: Optional[str] = None,
                   override_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        将单个 XYZ 文件转换为 GJF 文件
        
        参数:
            xyz_filepath: 输入 XYZ 文件路径
            gjf_filepath: 输出 GJF 文件路径（可选，默认与 XYZ 同名）
            override_config: 覆盖配置（可选）
            
        返回:
            转换成功返回 True，失败返回 False
        """
        try:
            xyz_path = Path(xyz_filepath)
            if not xyz_path.exists():
                logger.error(f"文件不存在：{xyz_filepath}")
                return False
            
            # 确定输出路径
            if gjf_filepath is None:
                gjf_filepath = str(xyz_path.with_suffix('.gjf'))
            
            # 合并配置
            config = {**self.config, **(override_config or {})}
            
            # 读取 XYZ 文件
            with open(xyz_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if len(lines) < 3:
                logger.error(f"XYZ 文件格式错误：{xyz_filepath}")
                return False
            
            atom_lines = lines[2:]
            
            # 写入 GJF 文件
            gjf_path = Path(gjf_filepath)
            with open(gjf_path, 'w', encoding='utf-8') as f:
                # 写入检查点文件路径
                chk_name = gjf_path.stem + config['chk_extension']
                f.write(f"%chk={chk_name}\n")
                
                # 写入路由部分
                job_type = config.get('job_type', 'Opt')
                f.write(f"# {config['method']}/{config['basis']} {job_type}\n\n")
                
                # 写入标题
                f.write(f"{config['title']}\n\n")
                
                # 写入电荷和自旋多重性
                f.write(f"{config['charge']} {config['multiplicity']}\n")
                
                # 写入原子坐标
                for line in atom_lines:
                    f.write(line)
                
                # 添加末尾空行（Gaussian 要求）
                f.write("\n")
            
            logger.info(f"已生成 GJF 文件：{gjf_filepath}")
            return True
            
        except Exception as e:
            logger.error(f"转换失败：{e}")
            return False
    
    def batch_convert(self, folder_path: str, 
                      pattern: str = '*.xyz',
                      remove_source: bool = False) -> Dict[str, int]:
        """
        批量转换文件夹中的 XYZ 文件
        
        参数:
            folder_path: 包含 XYZ 文件的文件夹路径
            pattern: 文件匹配模式（默认 *.xyz）
            remove_source: 是否删除源文件（默认 False）
            
        返回:
            统计字典：{'success': 成功数，'failed': 失败数}
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            logger.error(f"路径不是文件夹：{folder_path}")
            return {'success': 0, 'failed': 0}
        
        stats = {'success': 0, 'failed': 0}
        xyz_files = list(folder.glob(pattern))
        
        if not xyz_files:
            logger.warning(f"未找到匹配的 XYZ 文件：{pattern}")
            return stats
        
        logger.info(f"找到 {len(xyz_files)} 个 XYZ 文件，开始转换...")
        
        for xyz_file in xyz_files:
            gjf_file = xyz_file.with_suffix('.gjf')
            if self.xyz_to_gjf(str(xyz_file), str(gjf_file)):
                stats['success'] += 1
                if remove_source:
                    try:
                        xyz_file.unlink()
                        logger.debug(f"已删除源文件：{xyz_file.name}")
                    except Exception as e:
                        logger.warning(f"删除源文件失败：{e}")
            else:
                stats['failed'] += 1
        
        logger.info(f"转换完成：成功 {stats['success']} 个，失败 {stats['failed']} 个")
        return stats


def create_converter(config: Optional[Dict[str, Any]] = None) -> GJFConverter:
    """
    创建转换器实例的工厂函数
    
    参数:
        config: 配置字典
        
    返回:
        GJFConverter 实例
    """
    return GJFConverter(config)


if __name__ == "__main__":
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python xyz-gjf_refactored.py <文件夹路径> [方法/基组]")
        print("  示例：python xyz-gjf_refactored.py ./molecules B3LYP/6-311G(d)")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    
    # 解析可选的方法和基组
    config = {}
    if len(sys.argv) > 2:
        parts = sys.argv[2].split('/')
        if len(parts) >= 1:
            config['method'] = parts[0]
        if len(parts) >= 2:
            config['basis'] = parts[1]
    
    converter = create_converter(config if config else None)
    stats = converter.batch_convert(folder_path)
    
    print(f"\n转换完成!")
    print(f"  成功：{stats['success']} 个文件")
    print(f"  失败：{stats['failed']} 个文件")
