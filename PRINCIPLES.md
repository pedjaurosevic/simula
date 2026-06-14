# PRINCIPLES — pouke koje je serija testova zaradila

Ovaj fajl postoji da budući graditelj (čovek ili agent) ne vrati projekat u over-dizajn. Sve
ispod je *empirijski izvedeno* iz serije eksperimenata sa diskriminacijom tipa znaka na
Gemma 12B (lokalno, llama.cpp), ne stilska preferenca. Detalji su u istoriji projekta; ovde su
posledice za inženjering.

## 1. Failure mode 12B modela je PRETERANO OGRAĐIVANJE, ne lažno potvrđivanje.
Bez okvira, model odbija i validne zaključke. Replicirano kroz tri verzije (licenca-acc bare:
0.00 → 0.14 → 0.44; uvek najniže). Posledica: najvredniji deo prompta je *commit-direktiva*
(„obaveži se na konkretno, ne ograđuj se bez razloga"). U naraciji se to prevodi u: konkretan,
ukotvljen detalj umesto generičke kaše.

## 2. Sadržaj okvira je često nebitan; efekat je „pažnja/de-hedging", ne ontologija.
B' = B = 1.00: prazan hermeneutički žargon licencira isto kao imenovanje tačnih pojmova. Dva
puna uslova maksirala svaku stavku. Posledica: **ontologija/persona je dekoracija dok ablacija
ne dokaže suprotno.** Blueprint = pokazivači u materijal + sićušna kičma, ne velika ontologija.

## 3. Razrađena procedura ne pobeđuje prosto uokvirivanje — i ume da saplеte.
Operativni postupak C nije nadmašio priming, a na jednom slučaju (dim_masina) ga je sopstveni
kruti korak odveo u grešku koju je slobodniji model izbegao. Posledica: bez krutih
reasoning-šablona u sistem-promptu. Struktura ide na I/O granicu, ne u glavu modela.

## 4. State i činjenice žive IZVAN modela; model predlaže constrained delte.
Jedina struktura koja je radila svuda i nikad nije štetila bila je prisilan, parsabilan izlaz.
Posledica: GBNF (lokalno) / json_schema (OpenAI-compat) za delte; engine je izvor istine.

## 5. Drift je pravi front. Meri tamo gde model stvarno pada.
Plafon-saturisane metrike ničemu ne uče (blok-acc je bio 1.00 svuda → mrtav signal). Posledica:
ne troši merenje na ono što model već prolazi; ciljaj koherenciju na dugom horizontu
(narativni/činjenični drift), ne lepotu jednog poteza.

## 6. Eval rig je proizvod; skelet/prompt je potrošna roba.
Svaka intuicija „bogatije je bolje" pala je čim je dodata prava kontrola — tri puta. Posledica:
na 12B se ne veruje intuiciji o promptu; svaka izmena prolazi diferencijalni eval (uslov A/B +
ablacija + pre-registrovan prag). To je stalni deo sistema, ne jednokratni eksperiment.

## 7. Pouke su zavisne od skale.
Na 4B prazna rečitost ŠKODI, a imenovanje tipova pomaže (obrnuto od 12B). Posledica: ako
simulacra padne na manji model (fallback mašine), strategija prompta NIJE ista — više skeleta za
manje, manje za veće. Ne pretpostavljaj da 12B recept radi na 4B.

## 8. Gradi najtanje, rasti po dokazu.
Najjači potez cele serije bio bi: kreni od najtanjeg harnessa, dodaj komad po komad samo kad
ablacija pokaže deltu. To je inverzija planova koji skoruju visoko na *bogatstvu mašinerije* koje
ne mogu da pokažu da nešto radi. Tokeni i krutost se plaćaju; korist se dokazuje.
