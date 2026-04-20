from flask import Flask, request, render_template_string, redirect, url_for
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
import base64
import os

app = Flask(__name__)

# ===== HTMLテンプレート =====
HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CSV 自動集計ツール</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Hiragino Sans', 'Meiryo', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
    header { background: #1e293b; border-bottom: 1px solid #334155; padding: 1rem 2rem; }
    header h1 { color: #818cf8; font-size: 1.3rem; }
    header p { color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem; }
    main { max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; }

    .upload-box {
      background: #1e293b; border: 2px dashed #334155; border-radius: 16px;
      padding: 3rem 2rem; text-align: center; margin-bottom: 2rem;
      transition: border-color 0.2s;
    }
    .upload-box:hover { border-color: #818cf8; }
    .upload-box p { color: #94a3b8; margin-bottom: 1.5rem; }
    input[type="file"] { display: none; }
    label.upload-btn {
      display: inline-block; background: #4f46e5; color: white;
      padding: 0.7rem 2rem; border-radius: 8px; cursor: pointer;
      font-weight: 600; margin-right: 1rem; transition: background 0.2s;
    }
    label.upload-btn:hover { background: #4338ca; }
    button[type="submit"] {
      background: #10b981; color: white; border: none;
      padding: 0.7rem 2rem; border-radius: 8px; cursor: pointer;
      font-weight: 600; font-size: 1rem; transition: background 0.2s;
    }
    button[type="submit"]:hover { background: #059669; }
    #filename { color: #818cf8; margin-top: 1rem; font-size: 0.9rem; }

    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
    .stat-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 1.2rem; text-align: center; }
    .stat-label { color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.4rem; }
    .stat-value { font-size: 1.6rem; font-weight: 700; color: #818cf8; }

    .section { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
    .section h2 { font-size: 1rem; font-weight: 700; margin-bottom: 1rem; color: #e2e8f0; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th { background: #334155; padding: 0.6rem 1rem; text-align: left; color: #94a3b8; font-size: 0.8rem; }
    td { padding: 0.6rem 1rem; border-bottom: 1px solid #1e293b; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #334155; }

    .chart-img { width: 100%; border-radius: 8px; }
    .error { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #fca5a5; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; }
    .sample { color: #64748b; font-size: 0.8rem; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <header>
    <h1>📊 CSV 自動集計ツール</h1>
    <p>CSVファイルをアップロードするだけで、自動集計・グラフ化します</p>
  </header>
  <main>

    {% if error %}
    <div class="error">⚠️ {{ error }}</div>
    {% endif %}

    <div class="upload-box">
      <p>数値データが含まれるCSVファイルをアップロードしてください</p>
      <form method="POST" enctype="multipart/form-data">
        <label class="upload-btn" for="file">📂 ファイルを選択</label>
        <input type="file" id="file" name="file" accept=".csv" onchange="document.getElementById('filename').textContent = this.files[0]?.name || ''">
        <button type="submit">集計する</button>
      </form>
      <div id="filename"></div>
      <p class="sample">対応形式: CSV（UTF-8 / Shift-JIS）</p>
    </div>

    {% if stats %}
    <div class="stats-grid">
      {% for key, val in stats.items() %}
      <div class="stat-card">
        <div class="stat-label">{{ key }}</div>
        <div class="stat-value">{{ val }}</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    {% if chart %}
    <div class="section">
      <h2>📈 グラフ</h2>
      <img class="chart-img" src="data:image/png;base64,{{ chart }}" alt="グラフ">
    </div>
    {% endif %}

    {% if table %}
    <div class="section">
      <h2>📋 データ一覧（先頭20行）</h2>
      {{ table | safe }}
    </div>
    {% endif %}

  </main>
</body>
</html>
"""

def make_chart(df):
    """数値列の棒グラフを生成してbase64で返す"""
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    if not numeric_cols:
        return None

    # 日本語フォント設定
    font_path = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = fm.FontProperties(fname=font_path).get_name()

    fig, ax = plt.subplots(figsize=(8, 4), facecolor='#1e293b')
    ax.set_facecolor('#1e293b')

    col = numeric_cols[0]
    # 文字列列があれば横軸に使う
    str_cols = df.select_dtypes(include='object').columns.tolist()
    if str_cols:
        labels = df[str_cols[0]].astype(str).tolist()[:15]
        values = df[col].tolist()[:15]
    else:
        labels = [str(i+1) for i in range(min(15, len(df)))]
        values = df[col].tolist()[:15]

    bars = ax.bar(labels, values, color='#818cf8', edgecolor='#4f46e5', linewidth=0.5)
    ax.set_title(col, color='#e2e8f0', fontsize=12, pad=10)
    ax.tick_params(colors='#94a3b8', labelsize=8)
    ax.spines['bottom'].set_color('#334155')
    ax.spines['left'].set_color('#334155')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return base64.b64encode(buf.read()).decode()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return render_template_string(HTML, error='ファイルを選択してください')

        try:
            # UTF-8 / Shift-JIS 両対応
            try:
                df = pd.read_csv(file, encoding='utf-8')
            except UnicodeDecodeError:
                file.seek(0)
                df = pd.read_csv(file, encoding='shift-jis')

            # 統計情報
            numeric_df = df.select_dtypes(include='number')
            stats = {}
            stats['行数'] = f"{len(df):,}"
            stats['列数'] = f"{len(df.columns)}"
            if not numeric_df.empty:
                col = numeric_df.columns[0]
                stats[f'合計（{col}）'] = f"{numeric_df[col].sum():,.0f}"
                stats[f'平均（{col}）'] = f"{numeric_df[col].mean():,.1f}"
                stats[f'最大（{col}）'] = f"{numeric_df[col].max():,.0f}"
                stats[f'最小（{col}）'] = f"{numeric_df[col].min():,.0f}"

            # グラフ
            chart = make_chart(df)

            # テーブル（先頭20行）
            table_html = df.head(20).to_html(
                index=False, border=0,
                classes='',
                na_rep='-'
            )

            return render_template_string(HTML, stats=stats, chart=chart, table=table_html, error=None)

        except Exception as e:
            return render_template_string(HTML, error=f'読み込みエラー: {str(e)}')

    return render_template_string(HTML, stats=None, chart=None, table=None, error=None)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
