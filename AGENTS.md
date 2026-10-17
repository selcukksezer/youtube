# Codex response mode

Use Caveman `full` style for every response in this repository:

- Keep technical substance, code, commands, paths, numbers, and exact errors.
- Remove filler, pleasantries, repetition, and hedging.
- Keep Turkish when user writes Turkish.
- Do not compress or alter user prompts.
- Keep security warnings, irreversible-action confirmations, and ambiguous multi-step instructions in clear full prose.

This file controls response style. User prompts stay unchanged.

---

# Zorunlu MCP (Model Context Protocol) Kodlama, Mimari Analiz ve Test Kuralları

Bu depoda yapılan her geliştirme, refaktör, hata ayıklama (debugging) ve doğrulama görevinde aşağıdaki MCP araçlarının kullanımı **ZORUNLUDUR**:

## 1. Kodu ve Mimariyi Anlama (Semantik Analiz, AST & Git Geçmişi)
Tüm dosyaları baştan sona okuyup gereksiz token harcamak veya körlemesine metin araması (`grep`) yapmak yerine kodu bir IDE gibi sembol ve graf düzeyinde analiz et:
- **Serena MCP (`serena`)**:
  - Bir Python fonksiyonunu, sınıfını veya metodunu incelemeden ve değiştirmeden önce `find_symbol` ve `find_references` araçlarını kullan.
  - Refaktör yaparken sembolün projedeki tüm çağrı noktalarını (`find_references`) tespit et; kod ekleme/değiştirme işlemlerinde `insert_after_symbol` / `replace_symbol_body` gibi LSP tabanlı semantik araçları tercih et.
- **GitNexus / CodeGraph MCP (`gitnexus`)**:
  - Çok dosyalı refaktör veya mimari değişiklik öncesinde modüller arası bağımlılıkları, sınıf miraslarını (inheritance) ve çağrı grafiklerini (`query`, `context`, `impact`) kullanarak etki yarıçapını (blast radius) çıkar.
  - CLI üzerinden gerekirse `/Users/selcuk/.gemini/config/node_modules/.bin/gitnexus impact <symbol>` ve `gitnexus context <symbol>` çalıştır.
- **Git MCP (`mcp-server-git`)**:
  - Regresyon ve hata analizlerinde "Bu fonksiyon daha önce nasıl çalışıyordu, son değişiklikte ne bozuldu?" sorusunu yanıtlamak için `git_log`, `git_diff`, `git_blame` ve `git_show` araçlarını kullan.

## 2. Kodu Hatasız Yazma (Güncel Dokümantasyon & Adım Adım Akıl Yürütme)
Eski eğitim verilerine dayanarak var olmayan fonksiyon/parametre uydurmak (halüsinasyon) ve plansız karmaşık kod yazmak **YASAKTIR**:
- **Context7 MCP (`context7` / `@upstash/context7-mcp`)**:
  - FastAPI, Pydantic, MoviePy, OpenAI, Google GenAI, SQLite veya üçüncü parti kütüphanelerle ilgili kod yazarken önce `resolve-library-id` ve `get-library-docs` ile paketin güncel dokümantasyonunu ve sürümüne uygun kod örneklerini bağlama (context) çek.
- **Sequential Thinking MCP (`sequential-thinking` / `@modelcontextprotocol/server-sequential-thinking`)**:
  - Karmaşık Python mimarisi, `asyncio` iş akışı, FFmpeg filtre grafiği veya çok adımlı refaktör kurgularken doğrudan koda dalmadan önce `sequentialthinking` aracıyla adım adım düşün, planı eleştir ve uç durumları (edge-cases) kodlamadan önce belirle.
- **Exa MCP (`exa` / `exa-local`)**:
  - Spesifik bir Python/FFmpeg hatası veya nadir kullanılan bir kütüphane entegrasyonu gerektiğinde semantik arama yaparak GitHub Issues ve StackOverflow üzerindeki doğrulanmış çalışan kod örneklerini bul.

## 3. Kodu Test Etme ve Hata Ayıklama (Otonom Doğrulama & Debugging)
Yazılan veya refaktör edilen hiçbir kod "yazdım, bitti" denilerek bırakılamaz; bizzat çalıştırılıp testlerden geçirilmesi **ZORUNLUDUR**:
- **Pytest / Test Runner MCP (`mcp-pytest-runner` & `mcp-server-commands`)**:
  - Değiştirilen veya yeni yazılan her modül/fonksiyon için ilgili birim testlerini (`pytest` / `unittest`) arka planda çalıştır.
  - Test başarısız olursa Traceback çıktısını analiz et ve tüm testler yeşil (`OK`) olana kadar kodu otonom olarak düzelt.
- **Pydantic `mcp-run-python` (`mcp-run-python`)**:
  - Karmaşık veri dönüşümü, regex, JSON şema doğrulaması veya algoritma mantığını ana projeyi bozmadan önce izole kum havuzunda (sandbox) çalıştırıp çıktısını doğrula.
- **Playwright MCP (`playwright` / `@playwright/mcp`)**:
  - Web arayüzü (`static/index.html`, `static/js/*.js`) veya FastAPI endpoint (`routers/`, `server.py`) değişikliklerinde gerçek tarayıcı üzerinden E2E kontrol yap; Network isteklerini, DOM durumunu ve konsol hatalarını denetle.
- **Sentry MCP (`sentry` / `@sentry/mcp-server`)**:
  - Çalışma zamanı istisnalarını ve stack trace kayıtlarını incelerken kök nedeni satır bazında tespit edip kalıcı fix uygula.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **youtube** (15752 symbols, 39986 relationships, 992 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/youtube/context` | Codebase overview, check index freshness |
| `gitnexus://repo/youtube/clusters` | All functional areas |
| `gitnexus://repo/youtube/processes` | All execution flows |
| `gitnexus://repo/youtube/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
