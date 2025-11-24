#!/usr/bin/env python3
"""
直接调用 pytdx 测试板块与行业数据
"""

from pytdx.hq import TdxHq_API
import pandas as pd
import os
import shutil
import tempfile
import random
from urllib.request import urlopen
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import TDX_SERVERS

def _parse_block_name_info(incon_content: str):
    incon_content = incon_content.splitlines()
    incon_dict = []
    section = "Unknown"
    for i in incon_content:
        if len(i) <= 0:
            continue
        if i[0] == '#' and i[1] != '#':
            section = i[1:].strip("\n ")
        elif i[1] != '#':
            item = i.strip('\n ').split('|')
            incon_dict.append({
                'hycode': item[0],
                'blockname': item[-1],
                'type': section
            })
    return pd.DataFrame(incon_dict)

def _download_tdx_file(withZHB: bool = True):
    urls = [
        'http://www.tdx.com.cn/products/data/data/dbf/base.zip',
        'http://www.tdx.com.cn/products/data/data/dbf/gbbq.zip',
    ]
    tmpdir_root = tempfile.gettempdir()
    subdir_name = 'tdx_' + str(random.randint(0, 1000000))
    tmpdir = os.path.join(tmpdir_root, subdir_name)
    shutil.rmtree(tmpdir, ignore_errors=True)
    os.makedirs(tmpdir)
    try:
        for url in urls if withZHB else urls[:-1]:
            file = tmpdir + '/' + 'tmp.zip'
            f = urlopen(url)
            data = f.read()
            with open(file, 'wb') as code:
                code.write(data)
            f.close()
            shutil.unpack_archive(file, extract_dir=tmpdir)
            zhb = os.path.join(tmpdir, "zhb.zip")
            if os.path.exists(zhb):
                shutil.unpack_archive(zhb, extract_dir=tmpdir)
            os.remove(file)
    except Exception:
        pass
    return tmpdir

def _read_industry(folder: str):
    fhy = folder + '/tdxhy.cfg'
    try:
        with open(fhy, encoding='GB18030', mode='r') as f:
            hy = f.readlines()
        hy = [line.replace('\n', '') for line in hy]
        hy = pd.DataFrame(line.split('|') for line in hy)
        hy = hy[~hy[1].str.startswith('9')]
        hy = hy[~hy[1].str.startswith('2')]
        df = hy.rename({0: 'sse', 1: 'code', 2: 'tdx_code', 3: 'sw_code', 5: 'tdxrshy_code'}, axis=1). \
            reset_index(drop=True). \
            melt(id_vars=('sse', 'code'), value_name='hycode')
        return df
    except Exception:
        return pd.DataFrame()

def test_pytdx_blocks():
    print("=== 测试板块数据（pytdx） ===")
    api = TdxHq_API()
    s = TDX_SERVERS[0]
    with api.connect(s["ip"], s["port"]):
        files = [
            ("block.dat", "yb"),
            ("block_fg.dat", "fg"),
            ("block_gn.dat", "gn"),
            ("block_zs.dat", "zs"),
            ("hkblock.dat", "hk"),
            ("jjblock.dat", "jj"),
        ]
        dfs = []
        for fn, tp in files:
            try:
                df = api.to_df(api.get_and_parse_block_info(fn)).assign(blocktype=tp)
                dfs.append(df)
            except Exception:
                pass
        if not dfs:
            print("未获取到板块数据")
            return
        data = pd.concat(dfs, sort=False)
        print(f"原始记录数: {len(data)}")
        print(f"列: {list(data.columns)}")

        # 去重与过滤，仅统计A股常见代码段
        try:
            data["code"] = data["code"].astype(str)
        except Exception:
            pass

        def is_a_share(code: str) -> bool:
            return (
                code.startswith("000") or code.startswith("001") or code.startswith("002") or
                code.startswith("003") or code.startswith("200") or code.startswith("300") or
                code.startswith("301") or code.startswith("600") or code.startswith("601") or
                code.startswith("603") or code.startswith("605") or code.startswith("688")
            ) and len(code) == 6

        filt = data[data["code"].apply(is_a_share)]
        filt = filt.drop_duplicates(subset=["blockname", "code", "blocktype"], keep="first")

        gsize = filt.groupby(["blockname", "blocktype"]).size().sort_values(ascending=False)
        print(f"板块数量: {len(gsize)}")
        for (name, bt), cnt in gsize.head(10).items():
            try:
                codes = filt[(filt['blockname'] == name) & (filt['blocktype'] == bt)]["code"].head(5).tolist()
            except Exception:
                codes = []
            print(f"  - {name}: {cnt} 只股票 ({bt})")
            if codes:
                print(f"    示例股票: {', '.join(codes)}")

def test_pytdx_industries():
    print("=== 测试行业数据（pytdx） ===")
    api = TdxHq_API()
    s = TDX_SERVERS[0]
    with api.connect(s["ip"], s["port"]):
        incon_block_info = None
        try:
            content = api.get_block_dat_ver_up("incon.dat")
            if content:
                text = content.decode("GB18030")
                incon_block_info = _parse_block_name_info(text)
        except Exception:
            pass
        folder = _download_tdx_file(False if isinstance(incon_block_info, pd.DataFrame) else True)
        try:
            if not isinstance(incon_block_info, pd.DataFrame):
                incon_path = os.path.join(folder, "incon.dat")
                if not os.path.exists(incon_path):
                    zhb = os.path.join(folder, "zhb.zip")
                    if os.path.exists(zhb):
                        shutil.unpack_archive(zhb, extract_dir=folder)
                with open(incon_path, encoding='GB18030', mode='r') as f:
                    incon_content = f.read()
                incon_block_info = _parse_block_name_info(incon_content)
            df = _read_industry(folder).merge(incon_block_info, on='hycode')
            df.set_index('code', drop=False, inplace=True)
            g = df.groupby('hycode')
            print(f"行业数量: {len(g)}")
            for hycode, group in list(g)[:10]:
                name = group['blockname'].iloc[0]
                codes = group['code'].astype(str).head(5).tolist()
                print(f"  - {name}: {len(group)} 只股票 ({hycode})")
                if codes:
                    print(f"    示例股票: {', '.join(codes)}")
        except Exception as e:
            print(f"获取行业数据失败: {e}")
        finally:
            shutil.rmtree(folder, ignore_errors=True)

if __name__ == "__main__":
    test_pytdx_blocks()
    test_pytdx_industries()