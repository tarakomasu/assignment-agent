# 同梱ソフトウェア

アプリ本体のMITライセンスは第三者ソフトウェアのライセンスを変更しません。

| ソフトウェア | 用途 | ライセンス・参照先 |
| --- | --- | --- |
| Gemini CLI 0.47.0 | GoogleログインとPDFの解答生成 | Apache-2.0 https://github.com/google-gemini/gemini-cli |
| Node.js 22 | Gemini CLIの実行 | MITほか runtime/nodeとlicenses/Node-LICENSE |
| w64devkit 2.10.0 | Windows用GCC | GPL等 runtime/w64devkitのライセンス文書 |
| PythonとPyInstaller | Python不要の実行ファイル | PSF、GPLとbootloader例外等 licenses/python |
| python-docx・lxml | Word生成 | MIT・BSD等 licenses/python |
| Playwright・Chromium | 実測結果のPNG生成 | Apache-2.0・BSD等 runtime/browsers、licenses/python |
| pypdfほか | PDF検査・依存ライブラリ | BSD・MIT等 licenses/python |

w64devkitの正確な対応ソースを、Windows ZIPと同じGitHub Releaseに
`w64devkit-2.10.0-source.tar` として無償で同時配布します。
元の配布元：https://github.com/skeeto/w64devkit/releases/tag/v2.10.0
バイナリとソースのSHA256はリリースのSHA256SUMS.txtで確認できます。

Gemini CLIのnpmパッケージ内の第三者通知、Chromiumとw64devkitの付属文書は
省略せず配布します。Pythonライブラリの通知はlicenses/pythonにコピーします。
