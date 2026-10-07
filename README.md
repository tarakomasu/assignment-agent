# Assignment Agent

日本語の講義PDFから **今回提出するC言語課題をすべて** 読み取り、
講義で学んだ範囲のコードを生成して、コンパイル・テスト・仕様確認をした後にWordを作ります。
前回の課題の復習や解答例は提出対象に含めません。

## Windowsで使う

1. [Releases](https://github.com/tarakomasu/assignment-agent/releases/latest)から
   **assignment-agent-windows-x64.zip** をダウンロードします。
   「Code → Download ZIP」は開発用ソースなので、そちらを選ばないでください。
2. ZIPを右クリックして「すべて展開」します。ZIPの中から直接起動しないでください。
3. 展開した `assignment-agent` フォルダを開き、空いている場所を右クリックして
   「ターミナルで開く」を選びます。
4. 初回だけ、以下を実行します。

```powershell
.\assignment-agent.exe login
```

初回はGoogle公式のAntigravity CLIを自動でダウンロードし、公式配布情報のSHA512で検証します。
ブラウザで自分のGoogleアカウントにログインします。
ログインが終わってAntigravityの入力画面になったら `/quit` と入力して終了します。
ログイン情報はGoogle公式CLIが管理します。既存のAntigravityログインがあれば利用します。

5. 初回だけ、提出者の氏名と学籍番号を設定します。下の例を自分の情報に置き換えます。

```powershell
.\assignment-agent.exe profile --name "自分の氏名" --student-id "自分の学籍番号"
```

この情報はローカルに保存し、Wordの先頭に記載します。Googleへの課題処理の入力には含めません。
6. `input` フォルダに講義PDFを1つ置いて、次を実行します。

```powershell
.\assignment-agent.exe run
```

PDFの場所を直接指定することもできます。空白を含むパスは引用符で囲みます。

```powershell
.\assignment-agent.exe run "C:\Users\user\Downloads\第3回標準入力.pdf"
```

最後に表示された `output\実行日時\submission.docx` をWordで開き、
課題・コード・実行結果・提出条件を確認してください。
複数課題は1つのWordにまとめ、課題ごとに改ページします。
氏名など、PDFだけでは確定できない必須情報がある場合は処理を停止します。

**Python、Node.js、GCCの個別インストールは不要です。Google CLIは初回loginで自動導入します。**
インターネット接続とGoogleログインは必要です。Windows 10/11のx64版が対象です。
ZIPはPython実行環境・GCC・画像生成ブラウザを含むため大きめです。初回loginでも追加のダウンロードが発生します。OneDriveやネットワークドライブよりローカルのフォルダを推奨します。

## 出力

```text
output/実行日時/
  submission.docx         全課題をまとめたWord
  assignment.json         PDFから抽出した今回の課題とテスト
  review.json             PDFとの仕様照合結果
  manifest.json           実行情報
  task_01/
    solution.c           検証済みCコード
    tests.json           各入力・期待結果・実測結果
    result-01.png ...    実際のローカル実行を示す画像
```

課題を特定できない、コンパイル失敗、5秒以上の実行、期待結果との不一致、
PDFとの仕様照合失敗の場合は最大2回コードを修正します。
解決しない場合はWordを作成せずエラーを表示します。
実行ごとに新しいフォルダを使うので、以前のWordを今回の成功結果として表示しません。
`work` には失敗の原因や途中のデータを保存します。

## 困ったとき

```powershell
.\assignment-agent.exe doctor
```

- ログイン・利用上限のエラー：`login` を再実行します。Google側の利用上限に達した場合は時間をおいてください。
- 学校・会社のGoogleアカウント：Google Cloudプロジェクトの設定が必要な場合があります。
  アカウントの条件はGoogle公式のログイン案内に従ってください。
- ツールが見つからない：ZIPを「すべて展開」し、runtimeフォルダも残してください。
- inputにPDFが複数ある：1つにするか、`run "PDFのパス"` で指定します。
- パスワード付きPDF、20MBを超えるPDF、100ページを超えるPDFは対象外です。
- エラーが続く場合：`work/実行日時/failure.json` を確認します。

PDF全体・生成コード・検証結果はGoogleのGeminiへ送信されます。
認証情報はAntigravity CLIとOSの認証ストレージが管理し、アプリにはコピーしません。
ログアウトしたい場合は `login` で入力画面を開いて `/logout` を実行してください。
自動取得したCLI本体は `%LOCALAPPDATA%\AssignmentAgent\bin` に置きます。講義資料と出力も自動でGitHubに送信しません。
氏名・学籍番号の設定は `%LOCALAPPDATA%\AssignmentAgent\profile.json` に保存します。

## 実行と検証の範囲

PDFの仕様とテストを先に確定し、その後コードを生成します。
`gcc -std=c11 -Wall -Wextra` でコンパイルし、入力を渡した**実際のstdout**を
期待文字列と照合します。最後にGeminiが元のPDFとコード・実測値を別の呼び出しで確認します。
AIによる抽出や仕様確認は完全ではないため、提出前のWord確認が必要です。
Colabの画面を装った画像、課題で要求されていない感想や長い解説は追加しません。
実行結果画像はこのアプリの要件としてWordに含めます。

CコードはローカルPCで実行します。使用ヘッダ・関数の制限、実行時間制限、出力上限を設けていますが、
OSの隔離環境ではありません。ファイル・ネットワーク・外部コマンドを扱う課題は対象外です。

## 開発する

```text
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

開発時はGCCとGoogle公式のAntigravity CLIをインストールします。
macOSでは `~/.local/bin/agy` も自動検出します。

```text
python -m assignment_agent login
python -m assignment_agent run "講義.pdf"
python -m pytest -q
```

Googleに接続しないテストで、料金計算の実行・不一致・タイムアウト・出力上限・修正・
複数課題・Word生成・不正な応答・失敗時にWordを出さない動作を検証します。
Windows CIではZIP用exeを作成し、Python・Node・GCCをPATHから外した状態でも
同梱ツールだけでC実行からWord生成まで動くことを検証します（AI応答だけはオフラインのテスト用CLIで代替）。
Googleログインと実際のAI応答は利用者の端末で行い、CIに認証情報を入れません。

## Windows版を配布する

GitHub ActionsはmainへのpushでWindows ZIPを作り、Actionsの成果物として保存します。
`v0.1.0` のようなタグをpushすると、成功したビルドをGitHub Releasesに公開します。
配布物とSHA256SUMS.txt、Cコンパイラの対応ソースを同じリリースに置きます。
第三者ライセンスは [THIRD_PARTY.md](THIRD_PARTY.md) を参照してください。

Google側の接続は公式の[Antigravity CLIのGoogleログイン](https://www.antigravity.google/docs/cli/install/)、
[非対話実行](https://www.antigravity.google/docs/cli/headless/)に従います。
PDFの読み取り専用の主エージェントを使い、外部コマンド・ファイル書き込み・MCP・他エージェントのツールは渡しません。

従来のGemini CLIは2026年6月18日から個人向けGoogleログインの提供を終了しました。
そのため、本アプリではGoogle公式の後継CLIからGeminiモデルを呼び出します。
[Googleの移行告知](https://developers.googleblog.com/en/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)
