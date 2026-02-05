# ============================================
# 富山県観光 セグメント分析レポートアプリ
# ファイル名: app.py
# ============================================

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# ページ設定
st.set_page_config(
    page_title="富山県観光 セグメント分析レポート",
    page_icon="🏔️",
    layout="wide"
)

# ============================================
# データ読み込みとマッピング定義
# ============================================

@st.cache_data
def load_data():
    """データの読み込みとキャッシュ"""
    url = "https://docs.google.com/spreadsheets/d/1BZl1Gljcb1I9XuM_rbqB59uE7zEC2zJuq7M_mNbsQCs/export?format=csv"
    df = pd.read_csv(url)
    
    # 居住地コードの処理
    df['居住地_code'] = pd.to_numeric(df['居住地'], errors='coerce')
    
    # 福井県の抽出
    df.loc[df['居住地'] == '福井県', '居住地_code'] = 14
    fukui_mask = (df['居住エリア'] == 4) & (~df['居住地_code'].isin([3, 12, 1]))
    df.loc[fukui_mask, '居住地_code'] = 14
    
    return df

# マッピング定義
TARGET_REGIONS = {
    1: '富山県', 2: '東京都', 3: '石川県',
    4: '愛知県', 6: '大阪府', 7: '長野県', 14: '福井県'
}

REGION_ORDER = ['富山県', '東京都', '石川県', '愛知県', '大阪府', '長野県', '福井県']

COMPANION_MAP = {
    1: '子連れ家族(未就学児)', 2: '子連れ家族(小〜高校生)',
    3: '大人の家族', 4: '夫婦', 5: 'カップル',
    6: '友人・知人', 7: '団体旅行', 8: 'ひとり', 0: 'その他'
}

INCOME_MAP = {
    100: '100万円未満', 150: '100-200万円', 250: '200-300万円',
    350: '300-400万円', 500: '400-600万円', 700: '600-800万円',
    900: '800-1000万円', 1500: '1000-2000万円', 2000: '2000万円以上', 0: '無回答'
}

SUSHI_TYPE_MAP = {
    0: '食べていない', 1: '回転寿司店（チェーン店）', 2: '回転寿司店（地元）',
    3: '居酒屋・レストラン（チェーン店）', 4: '居酒屋・レストラン（地元）',
    5: '持ち帰り（道の駅・スーパーなど）', 6: '専門店'
}

MASUZUSHI_TYPE_MAP = {
    0: '食べていない', 1: '駅（売店・自販機など）', 2: '専門店',
    3: '居酒屋・レストラン（地元）', 4: '居酒屋・レストラン（チェーン店）',
    5: '回転寿司店（地元）', 6: '回転寿司店（チェーン店）',
    7: '持ち帰り（道の駅・スーパーなど）'
}

# レポート項目の定義
REPORT_SECTIONS = {
    '基本属性': 'basic',
    '旅行行動': 'travel',
    '交通手段': 'transport',
    '訪問目的': 'purpose',
    '情報源': 'info_source',
    '訪問先': 'visited',
    '消費額': 'expense',
    '満足度・NPS': 'satisfaction',
    '海の幸': 'seafood',
    '寿司・ます寿し': 'sushi'
}

# ============================================
# 分析関数
# ============================================

def get_region_data(df, region_name):
    """指定地域のデータを抽出"""
    df_with_region = df.copy()
    df_with_region['居住地名'] = df_with_region['居住地_code'].map(TARGET_REGIONS)
    return df_with_region[df_with_region['居住地名'] == region_name]

def get_all_target_data(df):
    """7地域全体のデータを抽出"""
    df_with_region = df.copy()
    df_with_region['居住地名'] = df_with_region['居住地_code'].map(TARGET_REGIONS)
    return df_with_region[df_with_region['居住地名'].notna()]

def calc_basic_stats(region_data, all_data):
    """基本属性の集計"""
    def calc_stats(data):
        n = len(data)
        if n == 0:
            return {}
        
        income_data = data[data['世帯年収'] > 0]['世帯年収']
        avg_income = income_data.mean() if len(income_data) > 0 else 0
        
        # 世帯年収の中央値に近いカテゴリを特定
        income_label = '不明'
        for code, label in sorted(INCOME_MAP.items()):
            if code > 0 and avg_income <= code:
                income_label = label
                break
        if avg_income > 1500:
            income_label = '1000-2000万円'
        
        stay_data = data['宿泊数（県内）']
        avg_stay = stay_data[stay_data > 0].mean() if (stay_data > 0).any() else 0
        
        # 同行者の最頻値
        companion_mode = data['同行者'].mode()
        companion_top = COMPANION_MAP.get(companion_mode.iloc[0], '不明') if len(companion_mode) > 0 else '不明'
        
        return {
            'サンプル数': n,
            '男性比率(%)': round((data['性別'] == 0).mean() * 100, 1),
            '女性比率(%)': round((data['性別'] == 1).mean() * 100, 1),
            '平均年代': f"{int(data['年代'].mean())}代",
            '最多同行者': companion_top,
            '平均宿泊数（県内）': round(avg_stay, 1),
            '平均世帯年収帯': income_label
        }
    
    region_stats = calc_stats(region_data)
    all_stats = calc_stats(all_data)
    
    return region_stats, all_stats

def calc_travel_stats(region_data, all_data):
    """旅行行動の集計"""
    def calc_stats(data):
        n = len(data)
        if n == 0:
            return {}
        
        stay_data = data['宿泊数（県内）']
        
        return {
            '宿泊率(%)': round((stay_data > 0).mean() * 100, 1),
            '平均宿泊数': round(stay_data[stay_data > 0].mean(), 1) if (stay_data > 0).any() else 0,
            '初訪問率(%)': round((data['来県回数'] == 1).mean() * 100, 1),
            'リピーター率(%)': round((data['来県回数'] >= 2).mean() * 100, 1),
            'ヘビーリピーター率(%)': round((data['来県回数'] >= 6).mean() * 100, 1)
        }
    
    return calc_stats(region_data), calc_stats(all_data)

def calc_transport_stats(df, region_data, all_data):
    """交通手段の集計"""
    primary_cols = [col for col in df.columns if col.startswith('1次交通_')]
    secondary_cols = [col for col in df.columns if col.startswith('県内交通_')]
    
    def calc_stats(data, cols, prefix):
        if len(data) == 0:
            return {}
        results = {}
        for col in cols:
            name = col.replace(prefix, '')
            results[name] = round(data[col].mean() * 100, 1)
        return results
    
    region_primary = calc_stats(region_data, primary_cols, '1次交通_')
    all_primary = calc_stats(all_data, primary_cols, '1次交通_')
    region_secondary = calc_stats(region_data, secondary_cols, '県内交通_')
    all_secondary = calc_stats(all_data, secondary_cols, '県内交通_')
    
    return {
        '1次交通': (region_primary, all_primary),
        '県内交通': (region_secondary, all_secondary)
    }

def calc_purpose_stats(df, region_data, all_data):
    """訪問目的の集計"""
    purpose_cols = [col for col in df.columns if col.startswith('訪問目的_')]
    
    def calc_stats(data):
        if len(data) == 0:
            return {}
        results = {}
        for col in purpose_cols:
            name = col.replace('訪問目的_', '')
            results[name] = round(data[col].mean() * 100, 1)
        return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))
    
    return calc_stats(region_data), calc_stats(all_data)

def calc_info_source_stats(df, region_data, all_data):
    """情報源の集計"""
    digital_cols = [col for col in df.columns if col.startswith('情報源（デジタル）_')]
    nondigital_cols = [col for col in df.columns if col.startswith('情報源（非デジタル）_')]
    
    def calc_stats(data, cols, prefix):
        if len(data) == 0:
            return {}
        results = {}
        for col in cols:
            name = col.replace(prefix, '')
            results[name] = round(data[col].mean() * 100, 1)
        return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))
    
    return {
        'デジタル': (calc_stats(region_data, digital_cols, '情報源（デジタル）_'),
                    calc_stats(all_data, digital_cols, '情報源（デジタル）_')),
        '非デジタル': (calc_stats(region_data, nondigital_cols, '情報源（非デジタル）_'),
                      calc_stats(all_data, nondigital_cols, '情報源（非デジタル）_'))
    }

def calc_visited_stats(df, region_data, all_data):
    """訪問先の集計"""
    visit_cols = [col for col in df.columns if col.startswith('訪問先_')]
    
    def calc_stats(data):
        if len(data) == 0:
            return {}
        results = {}
        for col in visit_cols:
            name = col.replace('訪問先_', '')
            results[name] = round(data[col].mean() * 100, 1)
        return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))
    
    return calc_stats(region_data), calc_stats(all_data)

def calc_expense_stats(region_data, all_data):
    """消費額の集計"""
    expense_cols = ['消費額（交通）', '消費額（飲食）', '消費額（宿泊）', 
                    '消費額（買い物）', '消費額（観光・体験）']
    
    def calc_stats(data):
        if len(data) == 0:
            return {}
        
        total = data[expense_cols].sum(axis=1)
        results = {
            '総消費額（平均）': f"{int(total.mean()):,}円",
            '総消費額（中央値）': f"{int(total.median()):,}円"
        }
        
        for col in expense_cols:
            name = col.replace('消費額（', '').replace('）', '')
            results[f'{name}（平均）'] = f"{int(data[col].mean()):,}円"
        
        return results
    
    return calc_stats(region_data), calc_stats(all_data)

def calc_satisfaction_stats(region_data, all_data):
    """満足度・NPSの集計"""
    sat_cols = ['満足度（2次交通）', '満足度（飲食）', '満足度（宿泊）', 
                '満足度（買い物）', '満足度（観光・体験）', '満足度（旅行全体）']
    
    def calc_stats(data):
        if len(data) == 0:
            return {}
        
        results = {}
        for col in sat_cols:
            name = col.replace('満足度（', '').replace('）', '')
            results[f'{name}満足度'] = round(data[col].mean(), 2)
        
        # NPSスコア
        nps_data = data['NPS']
        promoters = (nps_data >= 9).sum() / len(nps_data) * 100
        detractors = (nps_data <= 6).sum() / len(nps_data) * 100
        results['NPSスコア'] = round(promoters - detractors, 1)
        
        results['再来訪意向'] = round(data['再来訪意向'].mean(), 2)
        
        return results
    
    return calc_stats(region_data), calc_stats(all_data)

def calc_seafood_stats(df, region_data, all_data):
    """海の幸の集計（喫食率・感動率=感動転換率）"""
    eaten_cols = [col for col in df.columns if col.startswith('食べた海の幸_') and '食べていない' not in col]
    impressed_cols = [col for col in df.columns if col.startswith('感動した海の幸_') and '食べていない' not in col and '感動していない' not in col]
    
    seafood_names = [col.replace('食べた海の幸_', '') for col in eaten_cols]
    
    def calc_stats(data):
        if len(data) == 0:
            return {}, {}
        
        eaten_rates = {}
        conversion_rates = {}
        
        for seafood in seafood_names:
            eaten_col = f'食べた海の幸_{seafood}'
            impressed_col = f'感動した海の幸_{seafood}'
            
            if eaten_col in data.columns:
                eaten_rates[seafood] = round(data[eaten_col].mean() * 100, 1)
                
                if impressed_col in data.columns:
                    eaten_count = data[eaten_col].sum()
                    if eaten_count > 0:
                        impressed_count = data[impressed_col].sum()
                        conversion_rates[seafood] = round((impressed_count / eaten_count) * 100, 1)
                    else:
                        conversion_rates[seafood] = 0
        
        return eaten_rates, conversion_rates
    
    region_eaten, region_conv = calc_stats(region_data)
    all_eaten, all_conv = calc_stats(all_data)
    
    return {
        '喫食率': (region_eaten, all_eaten),
        '感動率': (region_conv, all_conv)
    }

def calc_sushi_stats(region_data, all_data):
    """寿司・ます寿しの集計"""
    def calc_stats(data):
        if len(data) == 0:
            return {}, {}
        
        # 寿司
        sushi_results = {
            '喫食率(%)': round((data['訪問した寿司店形態'] != 0).mean() * 100, 1)
        }
        for code, name in SUSHI_TYPE_MAP.items():
            if code != 0:
                sushi_results[name] = round((data['訪問した寿司店形態'] == code).mean() * 100, 1)
        
        # ます寿し
        masuzushi_results = {
            '喫食率(%)': round((data['訪問したます寿し店形態'] != 0).mean() * 100, 1)
        }
        for code, name in MASUZUSHI_TYPE_MAP.items():
            if code != 0:
                masuzushi_results[name] = round((data['訪問したます寿し店形態'] == code).mean() * 100, 1)
        
        return sushi_results, masuzushi_results
    
    region_sushi, region_masu = calc_stats(region_data)
    all_sushi, all_masu = calc_stats(all_data)
    
    return {
        '寿司': (region_sushi, all_sushi),
        'ます寿し': (region_masu, all_masu)
    }

# ============================================
# 表示関数
# ============================================

def display_comparison_table(title, region_stats, all_stats, region_name):
    """比較テーブルを表示"""
    st.subheader(title)
    
    data = []
    for key in region_stats.keys():
        data.append({
            '指標': key,
            region_name: region_stats.get(key, '-'),
            '全体': all_stats.get(key, '-')
        })
    
    if data:
        df_display = pd.DataFrame(data)
        st.table(df_display)

def display_ranking_table(title, region_stats, all_stats, region_name, top_n=10):
    """ランキング形式のテーブルを表示"""
    st.subheader(title)
    
    data = []
    for i, (key, value) in enumerate(list(region_stats.items())[:top_n], 1):
        data.append({
            '順位': i,
            '項目': key,
            f'{region_name}(%)': value,
            '全体(%)': all_stats.get(key, '-')
        })
    
    if data:
        df_display = pd.DataFrame(data)
        st.table(df_display)

# ============================================
# PDF生成関数
# ============================================

def generate_pdf_content(region_name, selected_sections, results):
    """PDFダウンロード用のテキストコンテンツを生成"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"富山県観光 セグメント分析レポート")
    lines.append(f"対象地域: {region_name}")
    lines.append("=" * 60)
    lines.append("")
    
    for section in selected_sections:
        if section == '基本属性' and 'basic' in results:
            region_stats, all_stats = results['basic']
            lines.append("■ 基本属性")
            lines.append("-" * 40)
            lines.append(f"{'指標':<20} {region_name:<15} {'全体':<15}")
            for key in region_stats.keys():
                lines.append(f"{key:<20} {str(region_stats.get(key, '-')):<15} {str(all_stats.get(key, '-')):<15}")
            lines.append("")
        
        elif section == '旅行行動' and 'travel' in results:
            region_stats, all_stats = results['travel']
            lines.append("■ 旅行行動")
            lines.append("-" * 40)
            lines.append(f"{'指標':<25} {region_name:<15} {'全体':<15}")
            for key in region_stats.keys():
                lines.append(f"{key:<25} {str(region_stats.get(key, '-')):<15} {str(all_stats.get(key, '-')):<15}")
            lines.append("")
        
        elif section == '交通手段' and 'transport' in results:
            lines.append("■ 交通手段")
            lines.append("-" * 40)
            
            for transport_type in ['1次交通', '県内交通']:
                region_stats, all_stats = results['transport'][transport_type]
                lines.append(f"\n【{transport_type}】")
                lines.append(f"{'交通手段':<25} {region_name}(%)<15 {'全体(%)':<15}")
                for key, value in sorted(region_stats.items(), key=lambda x: x[1], reverse=True)[:8]:
                    lines.append(f"{key:<25} {value:<15} {all_stats.get(key, '-'):<15}")
            lines.append("")
        
        elif section == '訪問目的' and 'purpose' in results:
            region_stats, all_stats = results['purpose']
            lines.append("■ 訪問目的 TOP10")
            lines.append("-" * 40)
            lines.append(f"{'順位':<5} {'訪問目的':<30} {region_name}(%)<12 {'全体(%)':<12}")
            for i, (key, value) in enumerate(list(region_stats.items())[:10], 1):
                lines.append(f"{i:<5} {key:<30} {value:<12} {all_stats.get(key, '-'):<12}")
            lines.append("")
        
        elif section == '情報源' and 'info_source' in results:
            lines.append("■ 情報源")
            lines.append("-" * 40)
            
            for source_type in ['デジタル', '非デジタル']:
                region_stats, all_stats = results['info_source'][source_type]
                lines.append(f"\n【{source_type}】")
                lines.append(f"{'順位':<5} {'情報源':<25} {region_name}(%)<12 {'全体(%)':<12}")
                for i, (key, value) in enumerate(list(region_stats.items())[:8], 1):
                    lines.append(f"{i:<5} {key:<25} {value:<12} {all_stats.get(key, '-'):<12}")
            lines.append("")
        
        elif section == '訪問先' and 'visited' in results:
            region_stats, all_stats = results['visited']
            lines.append("■ 訪問先 TOP10")
            lines.append("-" * 40)
            lines.append(f"{'順位':<5} {'訪問先':<25} {region_name}(%)<12 {'全体(%)':<12}")
            for i, (key, value) in enumerate(list(region_stats.items())[:10], 1):
                lines.append(f"{i:<5} {key:<25} {value:<12} {all_stats.get(key, '-'):<12}")
            lines.append("")
        
        elif section == '消費額' and 'expense' in results:
            region_stats, all_stats = results['expense']
            lines.append("■ 消費額")
            lines.append("-" * 40)
            lines.append(f"{'項目':<20} {region_name:<15} {'全体':<15}")
            for key in region_stats.keys():
                lines.append(f"{key:<20} {str(region_stats.get(key, '-')):<15} {str(all_stats.get(key, '-')):<15}")
            lines.append("")
        
        elif section == '満足度・NPS' and 'satisfaction' in results:
            region_stats, all_stats = results['satisfaction']
            lines.append("■ 満足度・NPS")
            lines.append("-" * 40)
            lines.append(f"{'項目':<20} {region_name:<15} {'全体':<15}")
            for key in region_stats.keys():
                lines.append(f"{key:<20} {str(region_stats.get(key, '-')):<15} {str(all_stats.get(key, '-')):<15}")
            lines.append("")
        
        elif section == '海の幸' and 'seafood' in results:
            lines.append("■ 海の幸")
            lines.append("-" * 40)
            
            for stat_type in ['喫食率', '感動率']:
                region_stats, all_stats = results['seafood'][stat_type]
                lines.append(f"\n【{stat_type}】")
                lines.append(f"{'海の幸':<15} {region_name}(%)<12 {'全体(%)':<12}")
                for key in region_stats.keys():
                    lines.append(f"{key:<15} {region_stats.get(key, '-'):<12} {all_stats.get(key, '-'):<12}")
            lines.append("")
        
        elif section == '寿司・ます寿し' and 'sushi' in results:
            lines.append("■ 寿司・ます寿し")
            lines.append("-" * 40)
            
            for sushi_type in ['寿司', 'ます寿し']:
                region_stats, all_stats = results['sushi'][sushi_type]
                lines.append(f"\n【{sushi_type}】")
                lines.append(f"{'項目':<30} {region_name}(%)<12 {'全体(%)':<12}")
                for key in region_stats.keys():
                    lines.append(f"{key:<30} {region_stats.get(key, '-'):<12} {all_stats.get(key, '-'):<12}")
            lines.append("")
    
    return "\n".join(lines)

# ============================================
# メインアプリ
# ============================================

def main():
    st.title("🏔️ 富山県観光 セグメント分析レポート")
    st.markdown("---")
    
    # データ読み込み
    with st.spinner("データを読み込んでいます..."):
        df = load_data()
    
    # サイドバー：選択UI
    st.sidebar.header("レポート設定")
    
    # 居住地選択
    selected_region = st.sidebar.selectbox(
        "居住地を選択",
        REGION_ORDER
    )
    
    # レポート項目選択
    st.sidebar.markdown("---")
    st.sidebar.subheader("レポート項目を選択（最大5つ）")
    
    selected_sections = []
    for section_name in REPORT_SECTIONS.keys():
        if st.sidebar.checkbox(section_name, value=(section_name in ['基本属性', '訪問目的', '満足度・NPS'])):
            selected_sections.append(section_name)
    
    # 5つ以上選択した場合の警告
    if len(selected_sections) > 5:
        st.sidebar.warning("⚠️ 5項目以上選択されています。最初の5項目のみ表示されます。")
        selected_sections = selected_sections[:5]
    
    # レポート生成ボタン
    st.sidebar.markdown("---")
    generate_button = st.sidebar.button("📊 レポート生成", type="primary", use_container_width=True)
    
    # メインエリア
    if generate_button or selected_sections:
        if not selected_sections:
            st.warning("レポート項目を1つ以上選択してください。")
            return
        
        # データ抽出
        region_data = get_region_data(df, selected_region)
        all_data = get_all_target_data(df)
        
        st.header(f"📍 {selected_region}からの来訪者レポート")
        st.caption(f"サンプル数: {len(region_data)}件（全体: {len(all_data)}件）")
        st.markdown("---")
        
        # 結果を格納する辞書
        results = {}
        
        # 各セクションの表示
        for section in selected_sections:
            
            if section == '基本属性':
                region_stats, all_stats = calc_basic_stats(region_data, all_data)
                results['basic'] = (region_stats, all_stats)
                display_comparison_table("■ 基本属性", region_stats, all_stats, selected_region)
            
            elif section == '旅行行動':
                region_stats, all_stats = calc_travel_stats(region_data, all_data)
                results['travel'] = (region_stats, all_stats)
                display_comparison_table("■ 旅行行動", region_stats, all_stats, selected_region)
            
            elif section == '交通手段':
                transport_results = calc_transport_stats(df, region_data, all_data)
                results['transport'] = transport_results
                
                st.subheader("■ 交通手段")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**【1次交通】**")
                    region_stats, all_stats = transport_results['1次交通']
                    data = []
                    for key, value in sorted(region_stats.items(), key=lambda x: x[1], reverse=True)[:8]:
                        data.append({'交通手段': key, f'{selected_region}(%)': value, '全体(%)': all_stats.get(key, '-')})
                    st.table(pd.DataFrame(data))
                
                with col2:
                    st.markdown("**【県内交通】**")
                    region_stats, all_stats = transport_results['県内交通']
                    data = []
                    for key, value in sorted(region_stats.items(), key=lambda x: x[1], reverse=True)[:8]:
                        data.append({'交通手段': key, f'{selected_region}(%)': value, '全体(%)': all_stats.get(key, '-')})
                    st.table(pd.DataFrame(data))
            
            elif section == '訪問目的':
                region_stats, all_stats = calc_purpose_stats(df, region_data, all_data)
                results['purpose'] = (region_stats, all_stats)
                display_ranking_table("■ 訪問目的 TOP10", region_stats, all_stats, selected_region, 10)
            
            elif section == '情報源':
                info_results = calc_info_source_stats(df, region_data, all_data)
                results['info_source'] = info_results
                
                st.subheader("■ 情報源")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**【デジタル】**")
                    region_stats, all_stats = info_results['デジタル']
                    data = []
                    for i, (key, value) in enumerate(list(region_stats.items())[:8], 1):
                        data.append({'順位': i, '情報源': key, f'{selected_region}(%)': value, '全体(%)': all_stats.get(key, '-')})
                    st.table(pd.DataFrame(data))
                
                with col2:
                    st.markdown("**【非デジタル】**")
                    region_stats, all_stats = info_results['非デジタル']
                    data = []
                    for i, (key, value) in enumerate(list(region_stats.items())[:8], 1):
                        data.append({'順位': i, '情報源': key, f'{selected_region}(%)': value, '全体(%)': all_stats.get(key, '-')})
                    st.table(pd.DataFrame(data))
            
            elif section == '訪問先':
                region_stats, all_stats = calc_visited_stats(df, region_data, all_data)
                results['visited'] = (region_stats, all_stats)
                display_ranking_table("■ 訪問先 TOP10", region_stats, all_stats, selected_region, 10)
            
            elif section == '消費額':
                region_stats, all_stats = calc_expense_stats(region_data, all_data)
                results['expense'] = (region_stats, all_stats)
                display_comparison_table("■ 消費額", region_stats, all_stats, selected_region)
            
            elif section == '満足度・NPS':
                region_stats, all_stats = calc_satisfaction_stats(region_data, all_data)
                results['satisfaction'] = (region_stats, all_stats)
                display_comparison_table("■ 満足度・NPS", region_stats, all_stats, selected_region)
            
            elif section == '海の幸':
                seafood_results = calc_seafood_stats(df, region_data, all_data)
                results['seafood'] = seafood_results
                
                st.subheader("■ 海の幸")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**【喫食率】**")
                    region_stats, all_stats = seafood_results['喫食率']
                    data = []
                    for key in region_stats.keys():
                        data.append({'海の幸': key, f'{selected_region}(%)': region_stats.get(key, '-'), '全体(%)': all_stats.get(key, '-')})
                    st.table(pd.DataFrame(data))
                
                with col2:
                    st.markdown("**【感動率】**")
                    region_stats, all_stats = seafood_results['感動率']
                    data = []
                    for key in region_stats.keys():
                        data.append({'海の幸': key, f'{selected_region}(%)': region_stats.get(key, '-'), '全体(%)': all_stats.get(key, '-')})
                    st.table(pd.DataFrame(data))
            
            elif section == '寿司・ます寿し':
                sushi_results = calc_sushi_stats(region_data, all_data)
                results['sushi'] = sushi_results
                
                st.subheader("■ 寿司・ます寿し")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**【寿司】**")
                    region_stats, all_stats = sushi_results['寿司']
                    data = []
                    for key in region_stats.keys():
                        data.append({'項目': key, f'{selected_region}(%)': region_stats.get(key, '-'), '全体(%)': all_stats.get(key, '-')})
                    st.table(pd.DataFrame(data))
                
                with col2:
                    st.markdown("**【ます寿し】**")
                    region_stats, all_stats = sushi_results['ます寿し']
                    data = []
                    for key in region_stats.keys():
                        data.append({'項目': key, f'{selected_region}(%)': region_stats.get(key, '-'), '全体(%)': all_stats.get(key, '-')})
                    st.table(pd.DataFrame(data))
            
            st.markdown("---")
        
        # PDFダウンロードボタン
        st.subheader("📥 レポートダウンロード")
        
        pdf_content = generate_pdf_content(selected_region, selected_sections, results)
        
        st.download_button(
            label="📄 テキストレポートをダウンロード",
            data=pdf_content.encode('utf-8'),
            file_name=f"富山県観光レポート_{selected_region}.txt",
            mime="text/plain"
        )

if __name__ == "__main__":
    main()
