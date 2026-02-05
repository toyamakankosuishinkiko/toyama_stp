# ============================================
# 富山県観光 セグメント分析レポートアプリ
# ファイル名: app.py
# 2地域比較対応版
# ============================================

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import urllib.request
import os

# ページ設定
st.set_page_config(
    page_title="富山県観光 セグメント分析レポート",
    page_icon="🏔️",
    layout="wide"
)

# ============================================
# 日本語フォント設定
# ============================================

@st.cache_resource
def setup_japanese_font():
    """日本語フォントのセットアップ"""
    font_url = "https://moji.or.jp/wp-content/ipafont/IPAexfont/IPAexfont00401.zip"
    font_path = "/tmp/ipaexg.ttf"
    
    if not os.path.exists(font_path):
        try:
            import zipfile
            zip_path = "/tmp/ipafont.zip"
            urllib.request.urlretrieve(font_url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("/tmp/")
            for root, dirs, files in os.walk("/tmp/"):
                for file in files:
                    if file == "ipaexg.ttf":
                        os.rename(os.path.join(root, file), font_path)
                        break
        except Exception as e:
            st.warning(f"日本語フォントの取得に失敗しました: {e}")
            return None
    
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('IPAexGothic', font_path))
        return 'IPAexGothic'
    return None

# ============================================
# データ読み込みとマッピング定義
# ============================================

@st.cache_data
def load_data():
    """データの読み込みとキャッシュ"""
    url = "https://docs.google.com/spreadsheets/d/1BZl1Gljcb1I9XuM_rbqB59uE7zEC2zJuq7M_mNbsQCs/export?format=csv"
    df = pd.read_csv(url)
    
    df['居住地_code'] = pd.to_numeric(df['居住地'], errors='coerce')
    
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

AGE_MAP = {10: '10代', 20: '20代', 30: '30代', 40: '40代',
           50: '50代', 60: '60代', 70: '70代', 80: '80代以上'}

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

def get_age_label(data):
    """年代のラベルを取得（最頻値を使用）"""
    if len(data) == 0:
        return '不明'
    
    ages_rounded = (data['年代'] // 10) * 10
    age_mode = ages_rounded.mode()
    
    if len(age_mode) > 0:
        age_value = int(age_mode.iloc[0])
        return AGE_MAP.get(age_value, f'{age_value}代')
    return '不明'

def calc_basic_stats(data):
    """基本属性の集計"""
    n = len(data)
    if n == 0:
        return {}
    
    income_data = data[data['世帯年収'] > 0]['世帯年収']
    avg_income = income_data.mean() if len(income_data) > 0 else 0
    
    income_label = '不明'
    for code, label in sorted(INCOME_MAP.items()):
        if code > 0 and avg_income <= code:
            income_label = label
            break
    if avg_income > 1500:
        income_label = '1000-2000万円'
    
    stay_data = data['宿泊数（県内）']
    avg_stay = stay_data[stay_data > 0].mean() if (stay_data > 0).any() else 0
    
    companion_mode = data['同行者'].mode()
    companion_top = COMPANION_MAP.get(companion_mode.iloc[0], '不明') if len(companion_mode) > 0 else '不明'
    
    age_label = get_age_label(data)
    
    return {
        'サンプル数': n,
        '男性比率(%)': round((data['性別'] == 0).mean() * 100, 1),
        '女性比率(%)': round((data['性別'] == 1).mean() * 100, 1),
        '最多年代': age_label,
        '最多同行者': companion_top,
        '平均宿泊数（県内）': round(avg_stay, 1),
        '平均世帯年収帯': income_label
    }

def calc_travel_stats(data):
    """旅行行動の集計"""
    n = len(data)
    if n == 0:
        return {}
    
    stay_data = data['宿泊数（県内）']
    
    return {
        '宿泊率(%)': round((stay_data > 0).mean() * 100, 1),
        '平均宿泊数': round(stay_data[stay_data > 0].mean(), 1) if (stay_data > 0).any() else 0.0,
        '初訪問率(%)': round((data['来県回数'] == 1).mean() * 100, 1),
        'リピーター率(%)': round((data['来県回数'] >= 2).mean() * 100, 1),
        'ヘビーリピーター率(%)': round((data['来県回数'] >= 6).mean() * 100, 1)
    }

def calc_transport_stats(df, data):
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
    
    return {
        '1次交通': calc_stats(data, primary_cols, '1次交通_'),
        '県内交通': calc_stats(data, secondary_cols, '県内交通_')
    }

def calc_purpose_stats(df, data):
    """訪問目的の集計"""
    purpose_cols = [col for col in df.columns if col.startswith('訪問目的_')]
    
    if len(data) == 0:
        return {}
    results = {}
    for col in purpose_cols:
        name = col.replace('訪問目的_', '')
        results[name] = round(data[col].mean() * 100, 1)
    return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))

def calc_info_source_stats(df, data):
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
        'デジタル': calc_stats(data, digital_cols, '情報源（デジタル）_'),
        '非デジタル': calc_stats(data, nondigital_cols, '情報源（非デジタル）_')
    }

def calc_visited_stats(df, data):
    """訪問先の集計"""
    visit_cols = [col for col in df.columns if col.startswith('訪問先_')]
    
    if len(data) == 0:
        return {}
    results = {}
    for col in visit_cols:
        name = col.replace('訪問先_', '')
        results[name] = round(data[col].mean() * 100, 1)
    return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))

def calc_expense_stats(data):
    """消費額の集計"""
    expense_cols = ['消費額（交通）', '消費額（飲食）', '消費額（宿泊）', 
                    '消費額（買い物）', '消費額（観光・体験）']
    
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

def calc_satisfaction_stats(data):
    """満足度・NPSの集計"""
    sat_cols = ['満足度（2次交通）', '満足度（飲食）', '満足度（宿泊）', 
                '満足度（買い物）', '満足度（観光・体験）', '満足度（旅行全体）']
    
    if len(data) == 0:
        return {}
    
    results = {}
    for col in sat_cols:
        name = col.replace('満足度（', '').replace('）', '')
        results[f'{name}満足度'] = round(data[col].mean(), 1)
    
    nps_data = data['NPS']
    promoters = (nps_data >= 9).sum() / len(nps_data) * 100
    detractors = (nps_data <= 6).sum() / len(nps_data) * 100
    results['NPSスコア'] = round(promoters - detractors, 1)
    
    results['再来訪意向'] = round(data['再来訪意向'].mean(), 1)
    
    return results

def calc_seafood_stats(df, data):
    """海の幸の集計"""
    eaten_cols = [col for col in df.columns if col.startswith('食べた海の幸_') and '食べていない' not in col]
    impressed_cols = [col for col in df.columns if col.startswith('感動した海の幸_') and '食べていない' not in col and '感動していない' not in col]
    
    seafood_names = [col.replace('食べた海の幸_', '') for col in eaten_cols]
    
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
                    conversion_rates[seafood] = 0.0
    
    return {'喫食率': eaten_rates, '感動率': conversion_rates}

def calc_sushi_stats(data):
    """寿司・ます寿しの集計"""
    if len(data) == 0:
        return {}, {}
    
    sushi_results = {
        '喫食率': round((data['訪問した寿司店形態'] != 0).mean() * 100, 1)
    }
    for code, name in SUSHI_TYPE_MAP.items():
        if code != 0:
            sushi_results[name] = round((data['訪問した寿司店形態'] == code).mean() * 100, 1)
    
    masuzushi_results = {
        '喫食率': round((data['訪問したます寿し店形態'] != 0).mean() * 100, 1)
    }
    for code, name in MASUZUSHI_TYPE_MAP.items():
        if code != 0:
            masuzushi_results[name] = round((data['訪問したます寿し店形態'] == code).mean() * 100, 1)
    
    return {'寿司': sushi_results, 'ます寿し': masuzushi_results}

# ============================================
# 表示関数（単一地域）
# ============================================

def display_single_comparison_table(title, region_stats, all_stats, region_name):
    """単一地域の比較テーブルを表示"""
    st.subheader(title)
    
    data = []
    for i, key in enumerate(region_stats.keys(), 1):
        region_val = region_stats.get(key, '-')
        all_val = all_stats.get(key, '-')
        
        if isinstance(region_val, float):
            region_val = f"{region_val:.1f}"
        if isinstance(all_val, float):
            all_val = f"{all_val:.1f}"
        
        data.append({
            'No': i,
            '指標': key,
            region_name: region_val,
            '全体': all_val
        })
    
    if data:
        df_display = pd.DataFrame(data)
        st.table(df_display.set_index('No'))

def display_single_ranking_table(title, region_stats, all_stats, region_name, top_n=10):
    """単一地域のランキングテーブルを表示"""
    st.subheader(title)
    
    data = []
    for i, (key, value) in enumerate(list(region_stats.items())[:top_n], 1):
        all_val = all_stats.get(key, '-')
        
        region_val_formatted = f"{value:.1f}" if isinstance(value, float) else value
        all_val_formatted = f"{all_val:.1f}" if isinstance(all_val, float) else all_val
        
        data.append({
            'No': i,
            '項目': key,
            f'{region_name}(%)': region_val_formatted,
            '全体(%)': all_val_formatted
        })
    
    if data:
        df_display = pd.DataFrame(data)
        st.table(df_display.set_index('No'))

# ============================================
# 表示関数（2地域比較）
# ============================================

def display_dual_comparison_table(title, stats1, stats2, all_stats, region1, region2):
    """2地域比較テーブルを表示"""
    st.subheader(title)
    
    all_keys = list(stats1.keys()) if stats1 else list(stats2.keys()) if stats2 else []
    
    data = []
    for i, key in enumerate(all_keys, 1):
        val1 = stats1.get(key, '-')
        val2 = stats2.get(key, '-')
        all_val = all_stats.get(key, '-')
        
        if isinstance(val1, float):
            val1 = f"{val1:.1f}"
        if isinstance(val2, float):
            val2 = f"{val2:.1f}"
        if isinstance(all_val, float):
            all_val = f"{all_val:.1f}"
        
        data.append({
            'No': i,
            '指標': key,
            region1: val1,
            region2: val2,
            '全体': all_val
        })
    
    if data:
        df_display = pd.DataFrame(data)
        st.table(df_display.set_index('No'))

def display_dual_ranking_table(title, stats1, stats2, all_stats, region1, region2, top_n=10):
    """2地域比較ランキングテーブルを表示"""
    st.subheader(title)
    
    # 地域1の順位をベースにする
    all_keys = list(stats1.keys())[:top_n] if stats1 else list(stats2.keys())[:top_n] if stats2 else []
    
    data = []
    for i, key in enumerate(all_keys, 1):
        val1 = stats1.get(key, '-')
        val2 = stats2.get(key, '-')
        all_val = all_stats.get(key, '-')
        
        val1_formatted = f"{val1:.1f}" if isinstance(val1, float) else val1
        val2_formatted = f"{val2:.1f}" if isinstance(val2, float) else val2
        all_val_formatted = f"{all_val:.1f}" if isinstance(all_val, float) else all_val
        
        data.append({
            'No': i,
            '項目': key,
            f'{region1}(%)': val1_formatted,
            f'{region2}(%)': val2_formatted,
            '全体(%)': all_val_formatted
        })
    
    if data:
        df_display = pd.DataFrame(data)
        st.table(df_display.set_index('No'))

# ============================================
# PDF生成関数
# ============================================

def generate_pdf_single(region_name, selected_sections, results):
    """単一地域PDF生成"""
    buffer = BytesIO()
    
    font_name = setup_japanese_font()
    if font_name is None:
        font_name = 'Helvetica'
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    if font_name == 'IPAexGothic':
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontName='IPAexGothic', fontSize=16, spaceAfter=10)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontName='IPAexGothic', fontSize=12, spaceAfter=6)
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontName='IPAexGothic', fontSize=9)
    else:
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
    
    elements.append(Paragraph(f"富山県観光 セグメント分析レポート", title_style))
    elements.append(Paragraph(f"対象地域: {region_name}", normal_style))
    elements.append(Spacer(1, 10))
    
    def create_table(data, col_widths=None):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name if font_name == 'IPAexGothic' else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        return table
    
    def format_val(val):
        if isinstance(val, float):
            return f"{val:.1f}"
        return str(val)
    
    for section in selected_sections:
        if section == '基本属性' and 'basic' in results:
            region_stats, all_stats = results['basic']
            elements.append(Paragraph("■ 基本属性", heading_style))
            data = [['No', '指標', region_name, '全体']]
            for i, key in enumerate(region_stats.keys(), 1):
                data.append([str(i), key, format_val(region_stats.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[10*mm, 50*mm, 45*mm, 45*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '旅行行動' and 'travel' in results:
            region_stats, all_stats = results['travel']
            elements.append(Paragraph("■ 旅行行動", heading_style))
            data = [['No', '指標', region_name, '全体']]
            for i, key in enumerate(region_stats.keys(), 1):
                data.append([str(i), key, format_val(region_stats.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[10*mm, 55*mm, 42*mm, 42*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '交通手段' and 'transport' in results:
            elements.append(Paragraph("■ 交通手段", heading_style))
            for transport_type in ['1次交通', '県内交通']:
                region_stats, all_stats = results['transport'][transport_type]
                elements.append(Paragraph(f"【{transport_type}】", normal_style))
                data = [['No', '交通手段', f'{region_name}(%)', '全体(%)']]
                for i, (key, value) in enumerate(sorted(region_stats.items(), key=lambda x: x[1], reverse=True)[:8], 1):
                    data.append([str(i), key, format_val(value), format_val(all_stats.get(key, '-'))])
                elements.append(create_table(data, col_widths=[10*mm, 55*mm, 42*mm, 42*mm]))
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 10))
        
        elif section == '訪問目的' and 'purpose' in results:
            region_stats, all_stats = results['purpose']
            elements.append(Paragraph("■ 訪問目的 TOP10", heading_style))
            data = [['No', '訪問目的', f'{region_name}(%)', '全体(%)']]
            for i, (key, value) in enumerate(list(region_stats.items())[:10], 1):
                data.append([str(i), key, format_val(value), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[10*mm, 70*mm, 35*mm, 35*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '情報源' and 'info_source' in results:
            elements.append(Paragraph("■ 情報源", heading_style))
            for source_type in ['デジタル', '非デジタル']:
                region_stats, all_stats = results['info_source'][source_type]
                elements.append(Paragraph(f"【{source_type}】", normal_style))
                data = [['No', '情報源', f'{region_name}(%)', '全体(%)']]
                for i, (key, value) in enumerate(list(region_stats.items())[:8], 1):
                    data.append([str(i), key, format_val(value), format_val(all_stats.get(key, '-'))])
                elements.append(create_table(data, col_widths=[10*mm, 70*mm, 35*mm, 35*mm]))
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 10))
        
        elif section == '訪問先' and 'visited' in results:
            region_stats, all_stats = results['visited']
            elements.append(Paragraph("■ 訪問先 TOP10", heading_style))
            data = [['No', '訪問先', f'{region_name}(%)', '全体(%)']]
            for i, (key, value) in enumerate(list(region_stats.items())[:10], 1):
                data.append([str(i), key, format_val(value), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[10*mm, 70*mm, 35*mm, 35*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '消費額' and 'expense' in results:
            region_stats, all_stats = results['expense']
            elements.append(Paragraph("■ 消費額", heading_style))
            data = [['No', '項目', region_name, '全体']]
            for i, key in enumerate(region_stats.keys(), 1):
                data.append([str(i), key, format_val(region_stats.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[10*mm, 50*mm, 45*mm, 45*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '満足度・NPS' and 'satisfaction' in results:
            region_stats, all_stats = results['satisfaction']
            elements.append(Paragraph("■ 満足度・NPS", heading_style))
            data = [['No', '項目', region_name, '全体']]
            for i, key in enumerate(region_stats.keys(), 1):
                data.append([str(i), key, format_val(region_stats.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[10*mm, 50*mm, 45*mm, 45*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '海の幸' and 'seafood' in results:
            elements.append(Paragraph("■ 海の幸", heading_style))
            for stat_type in ['喫食率', '感動率']:
                region_stats, all_stats = results['seafood'][stat_type]
                elements.append(Paragraph(f"【{stat_type}】", normal_style))
                data = [['No', '海の幸', f'{region_name}(%)', '全体(%)']]
                for i, key in enumerate(region_stats.keys(), 1):
                    data.append([str(i), key, format_val(region_stats.get(key, '-')), format_val(all_stats.get(key, '-'))])
                elements.append(create_table(data, col_widths=[10*mm, 50*mm, 45*mm, 45*mm]))
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 10))
        
        elif section == '寿司・ます寿し' and 'sushi' in results:
            elements.append(Paragraph("■ 寿司・ます寿し", heading_style))
            for sushi_type in ['寿司', 'ます寿し']:
                region_stats, all_stats = results['sushi'][sushi_type]
                elements.append(Paragraph(f"【{sushi_type}】", normal_style))
                data = [['No', '項目', f'{region_name}(%)', '全体(%)']]
                for i, key in enumerate(region_stats.keys(), 1):
                    data.append([str(i), key, format_val(region_stats.get(key, '-')), format_val(all_stats.get(key, '-'))])
                elements.append(create_table(data, col_widths=[10*mm, 65*mm, 37*mm, 37*mm]))
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 10))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_pdf_dual(region1, region2, selected_sections, results):
    """2地域比較PDF生成"""
    buffer = BytesIO()
    
    font_name = setup_japanese_font()
    if font_name is None:
        font_name = 'Helvetica'
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=10*mm,
        leftMargin=10*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    if font_name == 'IPAexGothic':
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontName='IPAexGothic', fontSize=16, spaceAfter=10)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontName='IPAexGothic', fontSize=12, spaceAfter=6)
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontName='IPAexGothic', fontSize=9)
    else:
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
    
    elements.append(Paragraph(f"富山県観光 セグメント分析レポート（2地域比較）", title_style))
    elements.append(Paragraph(f"比較対象: {region1} vs {region2}", normal_style))
    elements.append(Spacer(1, 10))
    
    def create_table(data, col_widths=None):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name if font_name == 'IPAexGothic' else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        return table
    
    def format_val(val):
        if isinstance(val, float):
            return f"{val:.1f}"
        return str(val)
    
    for section in selected_sections:
        if section == '基本属性' and 'basic' in results:
            stats1, stats2, all_stats = results['basic']
            elements.append(Paragraph("■ 基本属性", heading_style))
            data = [['No', '指標', region1, region2, '全体']]
            all_keys = list(stats1.keys()) if stats1 else list(stats2.keys())
            for i, key in enumerate(all_keys, 1):
                data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[8*mm, 45*mm, 35*mm, 35*mm, 35*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '旅行行動' and 'travel' in results:
            stats1, stats2, all_stats = results['travel']
            elements.append(Paragraph("■ 旅行行動", heading_style))
            data = [['No', '指標', region1, region2, '全体']]
            all_keys = list(stats1.keys()) if stats1 else list(stats2.keys())
            for i, key in enumerate(all_keys, 1):
                data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[8*mm, 50*mm, 33*mm, 33*mm, 33*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '交通手段' and 'transport' in results:
            elements.append(Paragraph("■ 交通手段", heading_style))
            for transport_type in ['1次交通', '県内交通']:
                stats1, stats2, all_stats = results['transport'][transport_type]
                elements.append(Paragraph(f"【{transport_type}】", normal_style))
                data = [['No', '交通手段', f'{region1}(%)', f'{region2}(%)', '全体(%)']]
                all_keys = list(dict(sorted(stats1.items(), key=lambda x: x[1], reverse=True)).keys())[:8]
                for i, key in enumerate(all_keys, 1):
                    data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
                elements.append(create_table(data, col_widths=[8*mm, 50*mm, 33*mm, 33*mm, 33*mm]))
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 10))
        
        elif section == '訪問目的' and 'purpose' in results:
            stats1, stats2, all_stats = results['purpose']
            elements.append(Paragraph("■ 訪問目的 TOP10", heading_style))
            data = [['No', '訪問目的', f'{region1}(%)', f'{region2}(%)', '全体(%)']]
            all_keys = list(stats1.keys())[:10] if stats1 else list(stats2.keys())[:10]
            for i, key in enumerate(all_keys, 1):
                data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[8*mm, 60*mm, 30*mm, 30*mm, 30*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '情報源' and 'info_source' in results:
            elements.append(Paragraph("■ 情報源", heading_style))
            for source_type in ['デジタル', '非デジタル']:
                stats1, stats2, all_stats = results['info_source'][source_type]
                elements.append(Paragraph(f"【{source_type}】", normal_style))
                data = [['No', '情報源', f'{region1}(%)', f'{region2}(%)', '全体(%)']]
                all_keys = list(stats1.keys())[:8] if stats1 else list(stats2.keys())[:8]
                for i, key in enumerate(all_keys, 1):
                    data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
                elements.append(create_table(data, col_widths=[8*mm, 55*mm, 30*mm, 30*mm, 30*mm]))
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 10))
        
        elif section == '訪問先' and 'visited' in results:
            stats1, stats2, all_stats = results['visited']
            elements.append(Paragraph("■ 訪問先 TOP10", heading_style))
            data = [['No', '訪問先', f'{region1}(%)', f'{region2}(%)', '全体(%)']]
            all_keys = list(stats1.keys())[:10] if stats1 else list(stats2.keys())[:10]
            for i, key in enumerate(all_keys, 1):
                data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[8*mm, 60*mm, 30*mm, 30*mm, 30*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '消費額' and 'expense' in results:
            stats1, stats2, all_stats = results['expense']
            elements.append(Paragraph("■ 消費額", heading_style))
            data = [['No', '項目', region1, region2, '全体']]
            all_keys = list(stats1.keys()) if stats1 else list(stats2.keys())
            for i, key in enumerate(all_keys, 1):
                data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[8*mm, 45*mm, 35*mm, 35*mm, 35*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '満足度・NPS' and 'satisfaction' in results:
            stats1, stats2, all_stats = results['satisfaction']
            elements.append(Paragraph("■ 満足度・NPS", heading_style))
            data = [['No', '項目', region1, region2, '全体']]
            all_keys = list(stats1.keys()) if stats1 else list(stats2.keys())
            for i, key in enumerate(all_keys, 1):
                data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
            elements.append(create_table(data, col_widths=[8*mm, 45*mm, 35*mm, 35*mm, 35*mm]))
            elements.append(Spacer(1, 10))
        
        elif section == '海の幸' and 'seafood' in results:
            elements.append(Paragraph("■ 海の幸", heading_style))
            for stat_type in ['喫食率', '感動率']:
                stats1, stats2, all_stats = results['seafood'][stat_type]
                elements.append(Paragraph(f"【{stat_type}】", normal_style))
                data = [['No', '海の幸', f'{region1}(%)', f'{region2}(%)', '全体(%)']]
                all_keys = list(stats1.keys()) if stats1 else list(stats2.keys())
                for i, key in enumerate(all_keys, 1):
                    data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
                elements.append(create_table(data, col_widths=[8*mm, 40*mm, 35*mm, 35*mm, 35*mm]))
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 10))
        
        elif section == '寿司・ます寿し' and 'sushi' in results:
            elements.append(Paragraph("■ 寿司・ます寿し", heading_style))
            for sushi_type in ['寿司', 'ます寿し']:
                stats1, stats2, all_stats = results['sushi'][sushi_type]
                elements.append(Paragraph(f"【{sushi_type}】", normal_style))
                data = [['No', '項目', f'{region1}(%)', f'{region2}(%)', '全体(%)']]
                all_keys = list(stats1.keys()) if stats1 else list(stats2.keys())
                for i, key in enumerate(all_keys, 1):
                    data.append([str(i), key, format_val(stats1.get(key, '-')), format_val(stats2.get(key, '-')), format_val(all_stats.get(key, '-'))])
                elements.append(create_table(data, col_widths=[8*mm, 55*mm, 32*mm, 32*mm, 32*mm]))
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 10))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============================================
# メインアプリ
# ============================================

def main():
    st.title("🏔️ 富山県観光 セグメント分析レポート")
    st.markdown("---")
    
    with st.spinner("データを読み込んでいます..."):
        df = load_data()
    
    st.sidebar.header("レポート設定")
    
    # 比較モード選択
    compare_mode = st.sidebar.radio(
        "比較モードを選択",
        ["単一地域レポート", "2地域比較レポート"]
    )
    
    st.sidebar.markdown("---")
    
    # 地域選択
    if compare_mode == "単一地域レポート":
        selected_region = st.sidebar.selectbox("居住地を選択", REGION_ORDER)
        selected_region2 = None
    else:
        selected_region = st.sidebar.selectbox("居住地①を選択", REGION_ORDER, index=1)  # 東京都
        remaining_regions = [r for r in REGION_ORDER if r != selected_region]
        selected_region2 = st.sidebar.selectbox("居住地②を選択", remaining_regions, index=3)  # 大阪府
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("レポート項目を選択（最大5つ）")
    
    selected_sections = []
    for section_name in REPORT_SECTIONS.keys():
        if st.sidebar.checkbox(section_name, value=(section_name in ['基本属性', '訪問目的', '満足度・NPS'])):
            selected_sections.append(section_name)
    
    if len(selected_sections) > 5:
        st.sidebar.warning("⚠️ 5項目以上選択されています。最初の5項目のみ表示されます。")
        selected_sections = selected_sections[:5]
    
    st.sidebar.markdown("---")
    generate_button = st.sidebar.button("📊 レポート生成", type="primary", use_container_width=True)
    
    if generate_button or selected_sections:
        if not selected_sections:
            st.warning("レポート項目を1つ以上選択してください。")
            return
        
        # データ抽出
        region_data1 = get_region_data(df, selected_region)
        all_data = get_all_target_data(df)
        
        if compare_mode == "2地域比較レポート":
            region_data2 = get_region_data(df, selected_region2)
            st.header(f"📍 {selected_region} vs {selected_region2} 比較レポート")
            st.caption(f"サンプル数: {selected_region}={len(region_data1)}件, {selected_region2}={len(region_data2)}件（全体: {len(all_data)}件）")
        else:
            st.header(f"📍 {selected_region}からの来訪者レポート")
            st.caption(f"サンプル数: {len(region_data1)}件（全体: {len(all_data)}件）")
        
        st.markdown("---")
        
        results = {}
        
        # ============================================
        # 単一地域モード
        # ============================================
        if compare_mode == "単一地域レポート":
            for section in selected_sections:
                if section == '基本属性':
                    region_stats = calc_basic_stats(region_data1)
                    all_stats = calc_basic_stats(all_data)
                    results['basic'] = (region_stats, all_stats)
                    display_single_comparison_table("■ 基本属性", region_stats, all_stats, selected_region)
                
                elif section == '旅行行動':
                    region_stats = calc_travel_stats(region_data1)
                    all_stats = calc_travel_stats(all_data)
                    results['travel'] = (region_stats, all_stats)
                    display_single_comparison_table("■ 旅行行動", region_stats, all_stats, selected_region)
                
                elif section == '交通手段':
                    region_transport = calc_transport_stats(df, region_data1)
                    all_transport = calc_transport_stats(df, all_data)
                    results['transport'] = {
                        '1次交通': (region_transport['1次交通'], all_transport['1次交通']),
                        '県内交通': (region_transport['県内交通'], all_transport['県内交通'])
                    }
                    
                    st.subheader("■ 交通手段")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**【1次交通】**")
                        region_stats, all_stats = results['transport']['1次交通']
                        data = []
                        for i, (key, value) in enumerate(sorted(region_stats.items(), key=lambda x: x[1], reverse=True)[:8], 1):
                            all_val = all_stats.get(key, '-')
                            data.append({'No': i, '交通手段': key, f'{selected_region}(%)': f"{value:.1f}", '全体(%)': f"{all_val:.1f}" if isinstance(all_val, float) else all_val})
                        st.table(pd.DataFrame(data).set_index('No'))
                    with col2:
                        st.markdown("**【県内交通】**")
                        region_stats, all_stats = results['transport']['県内交通']
                        data = []
                        for i, (key, value) in enumerate(sorted(region_stats.items(), key=lambda x: x[1], reverse=True)[:8], 1):
                            all_val = all_stats.get(key, '-')
                            data.append({'No': i, '交通手段': key, f'{selected_region}(%)': f"{value:.1f}", '全体(%)': f"{all_val:.1f}" if isinstance(all_val, float) else all_val})
                        st.table(pd.DataFrame(data).set_index('No'))
                
                elif section == '訪問目的':
                    region_stats = calc_purpose_stats(df, region_data1)
                    all_stats = calc_purpose_stats(df, all_data)
                    results['purpose'] = (region_stats, all_stats)
                    display_single_ranking_table("■ 訪問目的 TOP10", region_stats, all_stats, selected_region, 10)
                
                elif section == '情報源':
                    region_info = calc_info_source_stats(df, region_data1)
                    all_info = calc_info_source_stats(df, all_data)
                    results['info_source'] = {
                        'デジタル': (region_info['デジタル'], all_info['デジタル']),
                        '非デジタル': (region_info['非デジタル'], all_info['非デジタル'])
                    }
                    
                    st.subheader("■ 情報源")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**【デジタル】**")
                        region_stats, all_stats = results['info_source']['デジタル']
                        data = []
                        for i, (key, value) in enumerate(list(region_stats.items())[:8], 1):
                            all_val = all_stats.get(key, '-')
                            data.append({'No': i, '情報源': key, f'{selected_region}(%)': f"{value:.1f}", '全体(%)': f"{all_val:.1f}" if isinstance(all_val, float) else all_val})
                        st.table(pd.DataFrame(data).set_index('No'))
                    with col2:
                        st.markdown("**【非デジタル】**")
                        region_stats, all_stats = results['info_source']['非デジタル']
                        data = []
                        for i, (key, value) in enumerate(list(region_stats.items())[:8], 1):
                            all_val = all_stats.get(key, '-')
                            data.append({'No': i, '情報源': key, f'{selected_region}(%)': f"{value:.1f}", '全体(%)': f"{all_val:.1f}" if isinstance(all_val, float) else all_val})
                        st.table(pd.DataFrame(data).set_index('No'))
                
                elif section == '訪問先':
                    region_stats = calc_visited_stats(df, region_data1)
                    all_stats = calc_visited_stats(df, all_data)
                    results['visited'] = (region_stats, all_stats)
                    display_single_ranking_table("■ 訪問先 TOP10", region_stats, all_stats, selected_region, 10)
                
                elif section == '消費額':
                    region_stats = calc_expense_stats(region_data1)
                    all_stats = calc_expense_stats(all_data)
                    results['expense'] = (region_stats, all_stats)
                    display_single_comparison_table("■ 消費額", region_stats, all_stats, selected_region)
                
                elif section == '満足度・NPS':
                    region_stats = calc_satisfaction_stats(region_data1)
                    all_stats = calc_satisfaction_stats(all_data)
                    results['satisfaction'] = (region_stats, all_stats)
                    display_single_comparison_table("■ 満足度・NPS", region_stats, all_stats, selected_region)
                
                elif section == '海の幸':
                    region_seafood = calc_seafood_stats(df, region_data1)
                    all_seafood = calc_seafood_stats(df, all_data)
                    results['seafood'] = {
                        '喫食率': (region_seafood['喫食率'], all_seafood['喫食率']),
                        '感動率': (region_seafood['感動率'], all_seafood['感動率'])
                    }
                    
                    st.subheader("■ 海の幸")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**【喫食率】**")
                        region_stats, all_stats = results['seafood']['喫食率']
                        data = []
                        for i, key in enumerate(region_stats.keys(), 1):
                            region_val = region_stats.get(key, '-')
                            all_val = all_stats.get(key, '-')
                            data.append({'No': i, '海の幸': key, f'{selected_region}(%)': f"{region_val:.1f}" if isinstance(region_val, float) else region_val, '全体(%)': f"{all_val:.1f}" if isinstance(all_val, float) else all_val})
                        st.table(pd.DataFrame(data).set_index('No'))
                    with col2:
                        st.markdown("**【感動率】**")
                        region_stats, all_stats = results['seafood']['感動率']
                        data = []
                        for i, key in enumerate(region_stats.keys(), 1):
                            region_val = region_stats.get(key, '-')
                            all_val = all_stats.get(key, '-')
                            data.append({'No': i, '海の幸': key, f'{selected_region}(%)': f"{region_val:.1f}" if isinstance(region_val, float) else region_val, '全体(%)': f"{all_val:.1f}" if isinstance(all_val, float) else all_val})
                        st.table(pd.DataFrame(data).set_index('No'))
                
                elif section == '寿司・ます寿し':
                    region_sushi = calc_sushi_stats(region_data1)
                    all_sushi = calc_sushi_stats(all_data)
                    results['sushi'] = {
                        '寿司': (region_sushi['寿司'], all_sushi['寿司']),
                        'ます寿し': (region_sushi['ます寿し'], all_sushi['ます寿し'])
                    }
                    
                    st.subheader("■ 寿司・ます寿し")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**【寿司】**")
                        region_stats, all_stats = results['sushi']['寿司']
                        data = []
                        for i, key in enumerate(region_stats.keys(), 1):
                            region_val = region_stats.get(key, '-')
                            all_val = all_stats.get(key, '-')
                            data.append({'No': i, '項目': key, f'{selected_region}(%)': f"{region_val:.1f}" if isinstance(region_val, float) else region_val, '全体(%)': f"{all_val:.1f}" if isinstance(all_val, float) else all_val})
                        st.table(pd.DataFrame(data).set_index('No'))
                    with col2:
                        st.markdown("**【ます寿し】**")
                        region_stats, all_stats = results['sushi']['ます寿し']
                        data = []
                        for i, key in enumerate(region_stats.keys(), 1):
                            region_val = region_stats.get(key, '-')
                            all_val = all_stats.get(key, '-')
                            data.append({'No': i, '項目': key, f'{selected_region}(%)': f"{region_val:.1f}" if isinstance(region_val, float) else region_val, '全体(%)': f"{all_val:.1f}" if isinstance(all_val, float) else all_val})
                        st.table(pd.DataFrame(data).set_index('No'))
                
                st.markdown("---")
            
            # PDF出力（単一）
            st.subheader("📥 レポートダウンロード")
            pdf_buffer = generate_pdf_single(selected_region, selected_sections, results)
            st.download_button(
                label="📄 PDFレポートをダウンロード",
                data=pdf_buffer,
                file_name=f"富山県観光レポート_{selected_region}.pdf",
                mime="application/pdf"
            )
        
        # ============================================
        # 2地域比較モード
        # ============================================
        else:
            for section in selected_sections:
                if section == '基本属性':
                    stats1 = calc_basic_stats(region_data1)
                    stats2 = calc_basic_stats(region_data2)
                    all_stats = calc_basic_stats(all_data)
                    results['basic'] = (stats1, stats2, all_stats)
                    display_dual_comparison_table("■ 基本属性", stats1, stats2, all_stats, selected_region, selected_region2)
                
                elif section == '旅行行動':
                    stats1 = calc_travel_stats(region_data1)
                    stats2 = calc_travel_stats(region_data2)
                    all_stats = calc_travel_stats(all_data)
                    results['travel'] = (stats1, stats2, all_stats)
                    display_dual_comparison_table("■ 旅行行動", stats1, stats2, all_stats, selected_region, selected_region2)
                
                elif section == '交通手段':
                    transport1 = calc_transport_stats(df, region_data1)
                    transport2 = calc_transport_stats(df, region_data2)
                    all_transport = calc_transport_stats(df, all_data)
                    results['transport'] = {
                        '1次交通': (transport1['1次交通'], transport2['1次交通'], all_transport['1次交通']),
                        '県内交通': (transport1['県内交通'], transport2['県内交通'], all_transport['県内交通'])
                    }
                    
                    st.subheader("■ 交通手段")
                    for transport_type in ['1次交通', '県内交通']:
                        st.markdown(f"**【{transport_type}】**")
                        stats1, stats2, all_stats = results['transport'][transport_type]
                        data = []
                        all_keys = list(dict(sorted(stats1.items(), key=lambda x: x[1], reverse=True)).keys())[:8]
                        for i, key in enumerate(all_keys, 1):
                            data.append({
                                'No': i,
                                '交通手段': key,
                                f'{selected_region}(%)': f"{stats1.get(key, 0):.1f}",
                                f'{selected_region2}(%)': f"{stats2.get(key, 0):.1f}",
                                '全体(%)': f"{all_stats.get(key, 0):.1f}"
                            })
                        st.table(pd.DataFrame(data).set_index('No'))
                
                elif section == '訪問目的':
                    stats1 = calc_purpose_stats(df, region_data1)
                    stats2 = calc_purpose_stats(df, region_data2)
                    all_stats = calc_purpose_stats(df, all_data)
                    results['purpose'] = (stats1, stats2, all_stats)
                    display_dual_ranking_table("■ 訪問目的 TOP10", stats1, stats2, all_stats, selected_region, selected_region2, 10)
                
                elif section == '情報源':
                    info1 = calc_info_source_stats(df, region_data1)
                    info2 = calc_info_source_stats(df, region_data2)
                    all_info = calc_info_source_stats(df, all_data)
                    results['info_source'] = {
                        'デジタル': (info1['デジタル'], info2['デジタル'], all_info['デジタル']),
                        '非デジタル': (info1['非デジタル'], info2['非デジタル'], all_info['非デジタル'])
                    }
                    
                    st.subheader("■ 情報源")
                    for source_type in ['デジタル', '非デジタル']:
                        st.markdown(f"**【{source_type}】**")
                        stats1, stats2, all_stats = results['info_source'][source_type]
                        data = []
                        all_keys = list(stats1.keys())[:8]
                        for i, key in enumerate(all_keys, 1):
                            data.append({
                                'No': i,
                                '情報源': key,
                                f'{selected_region}(%)': f"{stats1.get(key, 0):.1f}",
                                f'{selected_region2}(%)': f"{stats2.get(key, 0):.1f}",
                                '全体(%)': f"{all_stats.get(key, 0):.1f}"
                            })
                        st.table(pd.DataFrame(data).set_index('No'))
                
                elif section == '訪問先':
                    stats1 = calc_visited_stats(df, region_data1)
                    stats2 = calc_visited_stats(df, region_data2)
                    all_stats = calc_visited_stats(df, all_data)
                    results['visited'] = (stats1, stats2, all_stats)
                    display_dual_ranking_table("■ 訪問先 TOP10", stats1, stats2, all_stats, selected_region, selected_region2, 10)
                
                elif section == '消費額':
                    stats1 = calc_expense_stats(region_data1)
                    stats2 = calc_expense_stats(region_data2)
                    all_stats = calc_expense_stats(all_data)
                    results['expense'] = (stats1, stats2, all_stats)
                    display_dual_comparison_table("■ 消費額", stats1, stats2, all_stats, selected_region, selected_region2)
                
                elif section == '満足度・NPS':
                    stats1 = calc_satisfaction_stats(region_data1)
                    stats2 = calc_satisfaction_stats(region_data2)
                    all_stats = calc_satisfaction_stats(all_data)
                    results['satisfaction'] = (stats1, stats2, all_stats)
                    display_dual_comparison_table("■ 満足度・NPS", stats1, stats2, all_stats, selected_region, selected_region2)
                
                elif section == '海の幸':
                    seafood1 = calc_seafood_stats(df, region_data1)
                    seafood2 = calc_seafood_stats(df, region_data2)
                    all_seafood = calc_seafood_stats(df, all_data)
                    results['seafood'] = {
                        '喫食率': (seafood1['喫食率'], seafood2['喫食率'], all_seafood['喫食率']),
                        '感動率': (seafood1['感動率'], seafood2['感動率'], all_seafood['感動率'])
                    }
                    
                    st.subheader("■ 海の幸")
                    for stat_type in ['喫食率', '感動率']:
                        st.markdown(f"**【{stat_type}】**")
                        stats1, stats2, all_stats = results['seafood'][stat_type]
                        data = []
                        all_keys = list(stats1.keys())
                        for i, key in enumerate(all_keys, 1):
                            data.append({
                                'No': i,
                                '海の幸': key,
                                f'{selected_region}(%)': f"{stats1.get(key, 0):.1f}",
                                f'{selected_region2}(%)': f"{stats2.get(key, 0):.1f}",
                                '全体(%)': f"{all_stats.get(key, 0):.1f}"
                            })
                        st.table(pd.DataFrame(data).set_index('No'))
                
                elif section == '寿司・ます寿し':
                    sushi1 = calc_sushi_stats(region_data1)
                    sushi2 = calc_sushi_stats(region_data2)
                    all_sushi = calc_sushi_stats(all_data)
                    results['sushi'] = {
                        '寿司': (sushi1['寿司'], sushi2['寿司'], all_sushi['寿司']),
                        'ます寿し': (sushi1['ます寿し'], sushi2['ます寿し'], all_sushi['ます寿し'])
                    }
                    
                    st.subheader("■ 寿司・ます寿し")
                    for sushi_type in ['寿司', 'ます寿し']:
                        st.markdown(f"**【{sushi_type}】**")
                        stats1, stats2, all_stats = results['sushi'][sushi_type]
                        data = []
                        all_keys = list(stats1.keys())
                        for i, key in enumerate(all_keys, 1):
                            data.append({
                                'No': i,
                                '項目': key,
                                f'{selected_region}(%)': f"{stats1.get(key, 0):.1f}",
                                f'{selected_region2}(%)': f"{stats2.get(key, 0):.1f}",
                                '全体(%)': f"{all_stats.get(key, 0):.1f}"
                            })
                        st.table(pd.DataFrame(data).set_index('No'))
                
                st.markdown("---")
            
            # PDF出力（2地域比較）
            st.subheader("📥 レポートダウンロード")
            pdf_buffer = generate_pdf_dual(selected_region, selected_region2, selected_sections, results)
            st.download_button(
                label="📄 PDFレポートをダウンロード",
                data=pdf_buffer,
                file_name=f"富山県観光レポート_{selected_region}_vs_{selected_region2}.pdf",
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()
