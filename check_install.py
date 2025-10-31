#!/usr/bin/env python3
"""
快速验证 TraderMCP 安装和配置
"""
import sys
import os

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python版本过低，需要3.8+")
        print(f"   当前版本: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'fastmcp',
        'ib_insync',
        'pandas',
        'pandas_market_calendars',
        'dotenv',
        'pydantic'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (未安装)")
            missing.append(package)
    
    if missing:
        print(f"\n缺少 {len(missing)} 个依赖包")
        print("运行以下命令安装: pip install -e .")
        return False
    
    print("\n✅ 所有依赖包已安装")
    return True


def check_config():
    """检查配置文件"""
    if not os.path.exists('.env'):
        print("❌ 未找到 .env 配置文件")
        print("   运行: cp .env.example .env")
        print("   然后编辑 .env 文件配置IB连接参数")
        return False
    
    print("✅ 找到 .env 配置文件")
    
    # 读取配置
    from dotenv import load_dotenv
    load_dotenv()
    
    ib_host = os.getenv('IB_HOST')
    ib_port = os.getenv('IB_PORT')
    ib_account = os.getenv('IB_ACCOUNT')
    
    if ib_account and ib_account != 'DU123456':
        print(f"✅ IB账户已配置: {ib_account}")
    else:
        print("⚠️  IB账户未配置或使用默认值")
        print("   请在 .env 中设置 IB_ACCOUNT")
    
    print(f"   IB Gateway: {ib_host}:{ib_port}")
    
    return True


def check_directories():
    """检查必要的目录"""
    dirs = ['data', 'logs']
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ 创建目录: {directory}/")
        else:
            print(f"✅ 目录存在: {directory}/")
    return True


def check_modules():
    """检查项目模块"""
    modules = [
        'src.config',
        'src.logger',
        'src.ib_client',
        'src.cache.db_manager',
        'src.risk.risk_manager',
        'src.tools.account',
        'src.tools.positions',
        'src.tools.orders',
        'src.tools.market_data',
        'src.tools.quotes',
        'src.tools.options',
        'src.tools.calendar',
        'src.tools.fundamentals'
    ]
    
    errors = []
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            errors.append((module, e))
    
    if errors:
        print(f"\n❌ {len(errors)} 个模块导入失败")
        return False
    
    print("\n✅ 所有模块导入成功")
    return True


def main():
    """主函数"""
    print("="*60)
    print("  TraderMCP 安装验证")
    print("="*60)
    print()
    
    checks = [
        ("Python版本", check_python_version),
        ("依赖包", check_dependencies),
        ("配置文件", check_config),
        ("目录结构", check_directories),
        ("项目模块", check_modules),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n【{name}】")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 检查失败: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    if all(results):
        print("✅ 所有检查通过！")
        print("\n下一步:")
        print("  1. 确保IB Gateway或TWS已启动")
        print("  2. 启用API连接")
        print("  3. 运行服务器: python -m src.server")
        print("  4. 或运行示例: python examples/usage_example.py")
        return 0
    else:
        print("❌ 部分检查未通过，请修复后重试")
        return 1


if __name__ == "__main__":
    sys.exit(main())
