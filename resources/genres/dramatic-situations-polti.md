# Polti's 36 Dramatic Situations — the conflict engine

Georges Polti (1895) catalogued what he argued are the only 36 dramatic situations any story can be
built from. Each situation is defined by **roles** (e.g., a Persecutor, a Suppliant, a Power in
authority) and a tension between them. The user's example engine uses these as a *hidden* table to
keep arcs dramatic; simula uses them the same way — as a **dramatic engine** the LLM draws on so it
always has a concrete conflict to commit to (PRINCIPLES.md #1: the failure mode is hedging into
generic mush; a named situation is an antidote).

These are genre-independent: "Revolt" works in Sci-Fi, Historical War, or Mythic Greece alike. That
is exactly why they belong in a **universal** blueprint.

## The 36 (canonical list)

1. Supplication — *Persecutor, Suppliant, a Power in authority*
2. Deliverance — *Unfortunate, Threatener, Rescuer*
3. Crime Pursued by Vengeance — *Avenger, Criminal*
4. Vengeance Taken for Kindred upon Kindred — *Avenging Kinsman, Guilty Kinsman, Victim*
5. Pursuit — *Punishment, Fugitive*
6. Disaster — *Vanquished Power, Victorious Enemy / Messenger*
7. Falling Prey to Cruelty or Misfortune — *Unfortunate, Master/Misfortune*
8. Revolt — *Tyrant, Conspirator(s)*
9. Daring Enterprise — *Bold Leader, Object, Adversary*
10. Abduction — *Abductor, Abducted, Guardian*
11. The Enigma — *Interrogator, Seeker, Problem*
12. Obtaining — *Solicitor, Adversary who refuses / Arbitrator*
13. Enmity of Kinsmen — *Malevolent Kinsman, Hated/Reciprocating Kinsman*
14. Rivalry of Kinsmen — *Preferred Kinsman, Rejected Kinsman, Object*
15. Murderous Adultery — *Two Adulterers, the Betrayed*
16. Madness — *Madman, Victim*
17. Fatal Imprudence — *Imprudent one, Victim/Lost object*
18. Involuntary Crimes of Love — *Lover, Beloved, Revealer*
19. Slaying of a Kinsman Unrecognized — *Slayer, Unrecognized Victim*
20. Self-Sacrifice for an Ideal — *Hero, Ideal, Person/Thing sacrificed*
21. Self-Sacrifice for Kindred — *Hero, Kinsman, Ideal sacrificed*
22. All Sacrificed for Passion — *Lover, Object of passion, Thing sacrificed*
23. Necessity of Sacrificing Loved Ones — *Hero, Beloved Victim, Necessity*
24. Rivalry of Superior and Inferior — *Superior Rival, Inferior Rival, Object*
25. Adultery — *Deceived Spouse, Two Adulterers*
26. Crimes of Love — *Lover, Beloved (taboo)*
27. Discovery of the Dishonor of a Loved One — *Discoverer, Guilty One*
28. Obstacles to Love — *Two Lovers, an Obstacle*
29. An Enemy Loved — *Beloved Enemy, Lover, Hater*
30. Ambition — *Ambitious one, Coveted Thing, Adversary*
31. Conflict with a God — *Mortal, Immortal*
32. Mistaken Jealousy — *Jealous one, Object, Supposed Accomplice, Cause/Author of mistake*
33. Erroneous Judgment — *Mistaken one, Victim of mistake, Cause, Guilty one*
34. Remorse — *Culprit, Victim, Interrogator*
35. Recovery of a Lost One — *Seeker, One found*
36. Loss of Loved Ones — *Kinsman slain, Kinsman spectator, Executioner*

## How the engine uses them (our design)

- The **blueprint** names a small set of `dramatic_engine.situations` that fit the distilled world
  (e.g., a PKD dystopia leans on *Revolt*, *The Enigma*, *Erroneous Judgment*, *Pursuit*).
- These stay **hidden from the player** (like the example engine) — they are levers for the LLM, not
  menu text.
- Each turn, the salience logic (PRINCIPLES + the loop) lets the LLM pick or sustain a situation and
  cast current NPCs/state into its roles. This is what gives a session a *spine* instead of drift.
- The fact ledger records which situations are active so they resolve coherently over a long arc.

## Sources
- [The Thirty-Six Dramatic Situations (Wikipedia)](https://en.wikipedia.org/wiki/The_Thirty-Six_Dramatic_Situations)
- [Georges Polti's 36 Dramatic Situations (changingminds.org)](http://changingminds.org/disciplines/storytelling/plots/polti_situations/polti_situations.htm)
