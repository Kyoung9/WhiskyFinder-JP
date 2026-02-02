# WhiskyFinder-JP
日本国内のウィスキー価格を横断検索し、最安値順で表示するWebアプリ。
個人の学習のために作ったものです！s

- 検索 → スクレイピング → 集計 → CSVダウンロード
- 通貨・単位: JPY
- 対象: 日本の通販・価格比較サイト

## 要件
- Python 3.11+

## セットアップ
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install
```
※ ビックカメラはBot対策のためPlaywrightが必須です。

### Poetryを使う場合
```bash
poetry lock
poetry install
poetry run python -m playwright install
```

## 起動
```bash
python run.py
```

## エンドポイント
- `GET /` 検索UI
- `GET /search?q=...` JSON結果
- `GET /download?q=...` CSVダウンロード（事前に検索実行が必要）

## CSV出力形式
- ファイル名: `whisky_results_YYYYMMDD_HHMM.csv`
- カラム: `title, price, source, url, total`
- `total = price`

## 環境変数
`.env` に設定可能。

- `WHISKYFINDER_MAX_PAGES`: 最大スクレイピングページ数（デフォルト: 3）
- `WHISKYFINDER_FILTER_BY_TITLE`: タイトル一致フィルタの有効化（デフォルト: true）
- `WHISKYFINDER_BICCAMERA_CATEGORY`: ビックカメラのカテゴリ指定（任意）
- `WHISKYFINDER_BICCAMERA_USE_PLAYWRIGHT`: ビックカメラでPlaywrightを使うか（デフォルト: true）
- `WHISKYFINDER_BICCAMERA_PLAYWRIGHT_BROWSER`: 使用ブラウザ（chromium/webkit/firefox、デフォルト: chromium）
- `WHISKYFINDER_BICCAMERA_PLAYWRIGHT_HEADLESS`: ヘッドレス実行（デフォルト: true）
- `WHISKYFINDER_BICCAMERA_PLAYWRIGHT_TIMEOUT_MS`: Playwrightタイムアウト（デフォルト: 45000）
- `WHISKYFINDER_BICCAMERA_PLAYWRIGHT_UA`: PlaywrightのUser-Agent（任意）
- `WHISKYFINDER_YODOBASHI_CATEGORY_URL`: ヨドバシ.comのカテゴリURL指定（任意）

## 検索・整形ルール
- 検索語の空白・全角空白を正規化してキャッシュキーを生成
- 結果は `total` 昇順 → `source` 昇順でソート
- 重複判定: `title + source + price` が同一なら1件に統合

## 信濃屋のカテゴリ固定
- 信濃屋検索は `ct755`（ウイスキー）カテゴリ固定

## テストスクリプト
```bash
python scripts/test_biccamera.py "アードベック 10年"
```

## スクレイピング方針（必須）
- 各サイトの robots.txt / 利用規約を遵守
- リクエスト間に待機（例: 1〜2秒）と再試行・バックオフを実装
- User-Agent を明示し、過度な同時リクエストを避ける
- キャッシュで重複アクセスを最小化

## キャッシュ方針
- 同一キーワードは24時間キャッシュ
- TTL(24h)経過後のみ再スクレイピング

## プロジェクト構成
```
app/
  routes/
  services/
  scrapers/
  models/
  storage/
  templates/
  static/
tests/
run.py
requirements.txt
```

## スクレイピング対象（バックログ）
### 価格比較 / 最安値探索
- [x] 価格.com（ウイスキーカテゴリ）

### マーケットプレイス / モール
- [ ] 楽天市場
- [ ] Yahoo!ショッピング
- [ ] Amazon.co.jp
- [ ] LOHACO
- [ ] au PAY マーケット
- [ ] Qoo10
- [ ] dショッピング
- [ ] JRE MALL

### 大型チェーン / リテール
- [ ] ビックカメラ.com
- [x] ヨドバシ.com
- [ ] カクヤス
- [ ] 酒のやまや（やまや宅配）
- [ ] リカーマウンテン（リカマン）
- [ ] イオンリカー ネットスーパー
- [ ] AEON de WINE
- [ ] 成城石井 公式オンラインショップ

### ウィスキー / 洋酒専門店
- [x]信濃屋 公式通販ショップ
- [x]武蔵屋 オンラインストア
- [x]武川蒸留酒販売
- [ ] ワールドリカー・ブルータス
- [ ] 六本木鈴酒
- [ ] リカーズハセガワ
- [ ] ハセキタオンライン
- [ ] 大和屋酒舗 オンラインショップ
- [ ] 鈴木酒販 ONLINE STORE
- [ ] マツザキ オンラインショップ
- [ ] WHISKY MEW
- [ ] モルトヤマ
- [ ] THE ULTIMATE SPIRITS
- [ ] 洋酒専門店 千雅
- [ ] 頃末商店

---

# 한국어 요약
일본 위스키 가격을 여러 쇼핑몰에서 수집해 최저가 순으로 보여주는 웹 앱입니다.

- 검색 → 스크래핑 → 정렬 → CSV 다운로드
- 현재 지원: 価格.com, 信濃屋, 武蔵屋, Mukawa Spirit, ビックカメラ, ヨドバシ.com
- `GET /search?q=...` JSON, `GET /download?q=...` CSV
- 캐시 TTL 24시간, `total` 오름차순 정렬

자세한 내용은 위의 일본어 섹션을 참고하세요.
