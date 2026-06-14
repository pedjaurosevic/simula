# simulacra — PLAN

> Lokalno-prvi pogon za generisanje i naseljavanje sazdanih svetova i persona iz
> korisnikovih materijala. Jedan engine, dva tipa blueprinta, jedinstven model entiteta.
> Ime nosi pitanje, ne tvrdnju: da li je sazdani um/svet stvaran? (PKD)

Ovaj dokument je interni plan. Javni README ide na engleski kasnije; ovde mislimo na srpskom.
Kod, šeme i config su na engleskom (prenosivost, GitHub).

---

## 0. Šta simulacra jeste (i šta NIJE)

**Jeste:** tanak harness koji (1) primi korisnikove materijale (knjige, tekstove), (2) iz njih
destiluje *blueprint* (kičmu sveta ili persone — uglavnom pokazivače u materijal + sićušan
sažetak), i (3) vodi interaktivno, stateful, memorijsko iskustvo u kome LLM **predlaže**
strukturisane promene, a engine **drži istinu**.

**Nije:** generator svetova „iz vazduha", elaborirana kognitivna arhitektura, ni fork Zorka.
Zork je fiksni autorisani svet; mi pravimo svet *iz korpusa*. (Vidi `PRINCIPLES.md` za zašto —
to su pouke iz naše serije eksperimenata, ne stil.)

Dve implementacije nad istim jezgrom:
- **simulacra worldbuilding** — TUI/web igra; korisnik prolazi kroz svet generisan iz njegovih
  knjiga. Osnovana ideja, gradimo je prvu.
- **simulacra persona** — isti koncept primenjen na stvaranje persone (Big Five / OCEAN supstrat
  preko IPIP-a, javni domen × korisnikov materijal). Druga faza.

I key ideja: persona stvorena u *persona* modu može da živi u svetu iz *worldbuilding* moda.
To NIJE dodatak — to je ono za šta jedinstven model entiteta i postoji (sekcija 4).

---

## 1. Jedinstven model entiteta — srce dizajna

Sve u simulacri je **simulakrum**:

```
Simulakrum = (Blueprint, State, Memory, Contract)
```

- **Blueprint** — destilovana kičma: ŠTA je entitet. Uglavnom pokazivači u materijale + kratak
  sažetak. NE velika ontologija (pouka B'=B: ontologija je dekoracija; grounding na tekst nosi
  posledicu).
- **State** — deterministički izvor istine koji drži *engine*, ne model.
- **Memory** — kratkoročno (prozor transkripta) + dugoročno (ledger činjenica, istorija) +
  pretraga (RAG) nad oboje. Ovo je „pamti".
- **Contract** — gramatika/šema koju LLM MORA da emituje da bi predložio deltu (naracija + promena
  stanja). Struktura na granici, slobodno rezonovanje unutra.

Iz ovoga sve sledi:
- **Svet** = simulakrum čije je stanje *okruženje* (mesta, predmeti, NPC-ovi, vreme), a petlja je
  istraživanje.
- **Persona** = simulakrum čije je stanje *agent* (raspoloženje, znanje, odnos, ciljevi), a petlja
  je razgovor.
- **NPC** = persona-simulakrum *ugnežden* u svet-simulakrum. Kad igrač priča s njim, svetska petlja
  delegira potez tog entiteta persona-petlji, pa rezultat vrati kao svetsku deltu.

Zato je persona-u-svetu **kompozicija simulakruma**, a ne nova mašinerija. Gradiš jednu apstrakciju
entiteta i dve šeme blueprinta; ukrštanje je besplatno (ali se *isporučuje* poslednje — sekcija 4).

---

## 2. Slojevi

```
┌─────────────────────────────────────────────────────────┐
│  Klijenti (tanki):  TUI (Textual)   |   Web UI (FastAPI) │
├─────────────────────────────────────────────────────────┤
│  simulacra-core (biblioteka)                             │
│   • Backend apstrakcija (llama.cpp lokalno | OpenAI-compat)│
│   • Constrained output (GBNF lokalno | json_schema/tools) │
│   • RAG (sqlite-vec + FTS5, e5-small embeddings)         │
│   • State engine (sqlite, izvor istine) + Fact ledger    │
│   • Memory (kratko/dugoročno + pretraga)                 │
│   • Turn loop (ORORO-minimal)                            │
│   • Eval rig (style-fidelity, drift, commit-rate)        │
├─────────────────────────────────────────────────────────┤
│  Blueprint sloj:  World blueprint  |  Persona blueprint  │
├─────────────────────────────────────────────────────────┤
│  Workspace:  ~/simulacra-workspace/  (sqlite, materijali) │
└─────────────────────────────────────────────────────────┘
```

Klijenti su tanki — sva logika je u `simulacra-core`. TUI i web su dve kože nad istim jezgrom.

---

## 3. Turn loop (ORORO-minimal)

Jedan potez, isti za svet i personu (razlika je samo u blueprintu i šemi delte):

1. **Observe** — primi korisnikov unos.
2. **Retrieve** — RAG dohvati relevantne odlomke iz materijala + relevantne činjenice iz ledgera
   (grounding protiv *narativnog* drifta, ne samo knjigovodstvenog).
3. **React** — sastavi MINIMALAN prompt: commit-direktiva + blueprint-kičma + dohvaćeni egzemplari
   + trenutno stanje + prozor transkripta + korisnikov unos.
4. **Constrain** — pozovi backend sa contract-om (GBNF lokalno / json_schema na OpenAI-compat).
   Izlaz = `{ narration, deltas[] }`, garantovano parsabilno.
5. **Validate & apply** — engine proveri delte protiv stanja i ledgera (odbij nevalidne — npr.
   uzmi predmet koji nije tu), primeni validne, upiši u ledger.
6. **Persist & render** — sačuvaj stanje, prikaži naraciju.

Commit-direktiva je najvredniji deo prompta (pouka iz testova: failure mode modela je ograđivanje
→ generička kaša). Sadržaj otprilike: *„Obaveži se na konkretan, opipljiv detalj ukorenjen u
teksturi ovog sveta/persone. Nikad ne uzmiči u generičku fantastiku ili neodređenost."*

---

## 4. Persona-u-svetu — moje mišljenje

Ideja je dobra i nije periferna: ona je *razlog* da model entiteta bude jedinstven. Ako su i svet i
persona „simulakrum = (blueprint, state, memory, contract)", onda je persona u svetu samo bogat NPC
— svetska petlja delegira njegov potez persona-petlji. Apstrakcija to dopušta od prvog dana, pa
treba da je projektujemo *unutra* odmah (uniformni entiteti), čak i pre nego što je iskoristimo.

Ali iskreno o ceni, da je ne gradimo prerano:
- Dva LLM-vođena entiteta sa svojim stanjem znače *dva* poziva po potezu (latencija) i
  *umnožen* rizik drifta — persona mora ostati dosledna sebi I uklopiti se u ton sveta.
- To je najteži slučaj koherencije. Pouka „meri gde pada": ne gradi najteže prvo.

Zato: **arhitektura to dozvoljava od starta, ali se isporučuje poslednje** (Faza 6), tek kad eval
rig pokaže da je drift *jednog* entiteta pod kontrolom. Voli ideju, odloži izvođenje.

---

## 5. Backend apstrakcija (lokalno-prvi, ali uvek OpenAI-compat)

Jedan interfejs, dva adaptera (vidi `simulacra/backends.py`):

```
complete(messages, *, contract=None, temperature, max_tokens) -> str
```

- **LlamaCppBackend** (primarno): HTTP na lokalni server (:18083). Constrained output preko
  **GBNF gramatike** (`grammar` polje) — garancija validnog JSON-a na nivou dekodiranja. Embeddings
  lokalno (e5-small). Ovo je default.
- **OpenAICompatBackend**: bilo koji OpenAI-kompatibilan endpoint + ključ + model. Constrained
  output preko `response_format: json_schema` ili tool-calling; fallback parse-and-repair petlja
  ako model ne podržava. Embeddings: ili njihov endpoint ili i dalje lokalni e5 (preporuka: lokalni
  e5, da se ne vezujemo).

Izbor backenda je u `simulacra.toml` u workspace-u. „Contract" je apstrakcija strukturisanog
izlaza koja se različito implementira po backendu — to je kičma pouzdanosti.

---

## 6. Workspace (instalira se na korisnikovoj mašini)

Lokacija preko `platformdirs` (cross-platform), default `~/simulacra-workspace/`:

```
simulacra-workspace/
  simulacra.toml          # config: backend, endpoint, model, ključ, mod iskustva
  materials/              # korisnikove knjige/tekstovi (njegovi, lokalno)
  library.sqlite          # RAG (sqlite-vec + FTS5) + state + memory + ledger
  blueprints/             # destilovani world/persona blueprintovi (JSON)
  saves/                  # snimci iskustva / transkripti
  evals/                  # rezultati eval rig-a
```

Korisnik ubacuje knjige kroz TUI ili web (koji ih kopira u `materials/` i pokrene ingest). Sve je
inspektabilno i prenosivo. **Ne isporučujemo korpus** — korisnik donosi svoj (sekcija 9).

---

## 7. Cross-platform

Jezgro je Python (Linux/Mac/Windows). Pravila:
- Bez Linux-only zavisnosti; `pathlib` svuda, nikakve bash pretpostavke u jezgru.
- TUI: **Textual** (moderan, cross-platform). Web: **FastAPI** + tanak frontend.
- sqlite-vec radi cross-platform; e5-small preko `sentence-transformers`/`llama.cpp` embeddinga.
- llama.cpp backend je samo HTTP ka serveru koji korisnik diže (ili koristi OpenAI-compat),
  pa jezgro ne zavisi od platforme servera.
- Workspace lokacije preko `platformdirs`.

Razvijaš na Linux Mint; CI testira i Win/Mac (matrica) pre svakog release-a.

---

## 8. Pouzdanost: protiv drifta

Dva nivoa drifta, dva leka:
- **Knjigovodstveni** (inventar, lokacija): state izvan modela + constrained delte + validacija u
  engine-u. Model predlaže, engine presuđuje.
- **Narativni/tonski/činjenični** (zaboravi ustanovljenu činjenicu, izneveri ton, protivreči se):
  RAG-grounding na materijale svakog poteza + **fact ledger** (tekući zapis ustanovljenih
  činjenica) koji se i dohvata i koristi za validaciju kontradikcija.

Drugi nivo je pravi teški problem (pouka „meri gde pada"). Inženjerska vrednost simulacre je tu, ne
u lepoti jednog poteza.

---

## 9. Copyright / IP (bitno za javni GitHub)

- Isporučuje se **engine, nikad korpus**. Korisnik donosi svoje knjige u `materials/`.
- Blueprint vadi *teksturu* (ton, motivi, struktura, leksikon kao pokazivače), ne reprodukuje
  tekst. Dodaj guard protiv dugih doslovnih pasusa u naraciji.
- Rezultat: svet *u teksturi* nekog autora, ne prepis. Pravna higijena i bolja umetnost.

---

## 10. Eval rig — kičma, ne naknadna misao

Prenamenjuje naš aparat iz serije testova (uslovi, ablacija, pre-registracija). Meri:
- **style-fidelity** — embedding-distanca izlaza do korpusa (da li zvuči kao svet/persona).
- **drift** — broj kontradikcija izlaza protiv fact ledgera kroz N poteza.
- **commit-rate** — udeo poteza sa konkretnim, ukotvljenim detaljem vs generička kaša
  (anti-mush; meri da li commit-direktiva radi).

Svaka izmena prompta/RAG-a/backenda prolazi brzu ablaciju pre usvajanja. Svaka faza ima eval-kapiju.

---

## 11. Persona blueprint — Big Five / OCEAN preko IPIP-a (a NE MBTI/16Personalities)

Supstrat persone je **Big Five / OCEAN**, instanciran preko **IPIP** stavki — koje su u
**javnom domenu** (https://ipip.ori.org), slobodne za kopiranje, izmenu, prevod i komercijalnu
upotrebu, bez dozvole i naknade. To je svestan izbor i pravni i naučni:

- **Pravno (bitno za javni GitHub release):** MBTI je žig firme Myers-Briggs i licenciran
  instrument; 16Personalities NIJE MBTI nego NERIS okvir sa sopstvenim brendom, opisima, imenima
  arhetipova („Advocate" itd.) i grafikom — sve njihova svojina. Ne reprodukujemo njihov tekst,
  imena tipova ni brend. Sama tipologija (ideja osa, četvoroslovne oznake) nije pod copyrightom,
  ali pošto isporučujemo javni, komercijalno upotrebljiv engine, ne oslanjamo se na „hobi/lično"
  izuzetak — biramo čist javni-domen supstrat. (Ovo nije pravni savet; specifike variraju
  Srbija/EU vs SAD korisnici repa.)
- **Naučno:** OCEAN je empirijski robustan i falsifikabilan, za razliku od MBTI dihotomija. To se
  poklapa sa etosom serije testova (PRINCIPLES.md): merljivo i pošteno, ne klinička tvrdnja.

Mapiranje: pet **kontinuiranih** osa (O, C, E, A, N u [0,1]) → tendencije ponašanja, registar/glas
(iz materijala ako je persona „po" korpusu), vrednosti, manir, sopstvena „istorija" u memoriji.
Ako za generativnu udobnost zatreba diskretan seme, kontinuirane skorove **bukujemo u sopstvene
arhetipove sa sopstvenim imenima i opisima** (`archetype` polje, opciono) — nikad tuđa imena ni
tekst. Vidi `schemas/persona_blueprint.schema.json` (`ocean` umesto stare `lattice`).

---

## 12. Faze gradnje (svaka sa eval-kapijom)

- **Faza 0 — skelet.** Workspace bootstrap, config, backend adapter (llama.cpp + openai), contract
  apstrakcija, „hello world" turn loop end-to-end na *praznom* sadržaju. (Prvo radi end-to-end na
  praznom, pa dodaj komade.)
- **Faza 1 — ingest + RAG.** Ubaci knjige → chunk → embed → retrieve. Kapija: relevantnost
  dohvata na ručnim upitima.
- **Faza 2 — worldbuilding (osnovana ideja).** World DISTILL (korpus → world blueprint) +
  worldbuilding PLAY loop + STATE + fact ledger. TUI klijent. Prvi igrivi svet: **Kipple** (PKD).
- **Faza 3 — eval rig.** style-fidelity, drift, commit-rate; ablatiraj izbore prompta/RAG-a.
  Kapija: drift pod kontrolom kroz dugu sesiju.
- **Faza 4 — persona.** Persona DISTILL (OCEAN/IPIP supstrat × materijal → persona blueprint) + persona
  PLAY loop (razgovor, doslednost).
- **Faza 5 — web UI.** Tanak klijent nad jezgrom (FastAPI). Ubacivanje knjiga kroz web.
- **Faza 6 — persona-u-svetu.** Uniformni model entiteta se isplati: persona kao bogat NPC.
  Tek kad Faza 3 pokaže kontrolisan drift jednog entiteta.

Pravilo kroz sve faze: dodaj komponentu samo kad ablacija pokaže deltu ili spreči regresiju.
Najtanji harness koji radi, pa rast po dokazu — inverzija „970/1000 bogatstva mašinerije".

---

## 13. Eksplicitni ne-ciljevi (anti-inflacija)

- Bez velike svetske ontologije u promptu (pokazivači + kičma umesto toga).
- Bez krutih višekoračnih reasoning-šablona u sistem-promptu (krutost škodi — vidi dim_masina
  u `PRINCIPLES.md`).
- Bez self-modifying „super-exo" sloja u v1 (defeasible heuristike kasnije, ako ablacija traži).
- Bez LangChain-a i teških apstrakcija — direktni pozivi.
- Bez forka Z-machine/Zorka — pogrešan temelj za korpus→svet.
