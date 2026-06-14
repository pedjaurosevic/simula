# simula

**Lokalno-prvi pogon za sazdavanje i naseljavanje svetova i persona iz korisnikovih materijala.**

Jedan engine, dva tipa blueprinta (`world` | `persona`), jedinstven model entiteta
(`Simulacrum`). Lokalno-prvi (llama.cpp + GBNF za tvrdo ograničen izlaz), ali uvek može da radi
i protiv bilo kog OpenAI-kompatibilnog endpointa.

> **Status:** rana alfa (Phase 0). Jezgro je još uvek skelet — vidi `PLAN.md` za faze
> implementacije i `PRINCIPLES.md` za empirijski izvedene pouke koje vode dizajn.

## Instalacija

```bash
pip install simula
```

## Brzi start

```bash
simula --version
simula init          # napravi workspace (materials/ blueprints/ saves/ evals/)
simula where         # ispiši putanju workspace-a
```

Workspace ide na platform-default putanju (preko `platformdirs`), uz fallback na
`~/simula-workspace`. Korpus nikad nije isporučen — ti donosiš svoje materijale.

## Konfiguracija

Kopiraj `simula.toml.example` u workspace kao `simula.toml` i uredi backend (llama.cpp ili
OpenAI-kompatibilni), embeddinge, RAG i mod doživljaja (`world` | `persona`).

## Dizajn ukratko

- **Constrained output** je kičma pouzdanosti: GBNF na llama.cpp `/completion`, `json_schema`
  na OpenAI-kompatibilnom backendu, uz parse-and-repair fallback.
- **Minimalan prompt:** commit-direktiva + kičma blueprinta + pokazivači u materijale (RAG),
  ne velika ontologija.
- **Lokalno-prvi i privatno:** embeddinzi i generacija mogu ostati na tvojoj mašini.

## Licenca

MIT — vidi [LICENSE](LICENSE).
