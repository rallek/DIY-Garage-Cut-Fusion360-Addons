# Mitmachen und Arbeiten

Dieses Projekt arbeitet nach einem klaren Issue- und Pull-Request-Modell.

## Grundregeln

- Jedes Thema bekommt genau ein GitHub-Issue.
- Zu jedem Issue gibt es genau einen Arbeits-Thread.
- Zu jedem Issue gibt es genau einen Pull Request.
- Ein PR soll nur ein fachlich zusammenhängendes Thema enthalten.
- `main` wird nicht direkt bearbeitet, sondern nur über Pull Requests.
- Als Review reicht in diesem Projekt ein sauber dokumentierter Codex-Review-Thread oder eine gleichwertige technische Selbstprüfung.
- Ein zweites menschliches GitHub-Approval ist für dieses Solo-Setup nicht verpflichtend.
- Das eigentliche Mergen auf GitHub machst du selbst.
- Ich bereite Branch, Commit und Pull Request vor, aber ich führe keinen Merge aus.

## Arbeitsablauf

1. Issue anlegen oder ein bestehendes Issue auswählen.
2. Einen Branch pro Issue erstellen.
3. Im Issue diskutieren und Entscheidungen festhalten.
4. Code und Doku im gleichen PR umsetzen.
5. PR mit dem Issue verknüpfen.
6. Du mergst den PR auf GitHub selbst.
7. Danach wird das Issue geschlossen.

## Definition of Done

Ein Issue gilt erst als fertig, wenn:

- die technische Umsetzung vorhanden ist
- die Dokumentation angepasst wurde
- eine sinnvolle Prüfung oder ein Test vorhanden ist
- der Pull Request referenziert und zusammengeführt wurde
- das Issue abgeschlossen werden kann
- die Prüfung nachvollziehbar dokumentiert ist, auch wenn sie nicht als formales GitHub-Approval einer zweiten Person vorliegt

## Branch-Namen

Empfohlenes Schema:

```text
codex/issue-<nummer>-<kurzname>
```

## Kommentar- und Diskussionsregeln

- Offene fachliche Fragen werden im Issue geklärt.
- Entscheidungen werden im Issue dokumentiert, nicht nur im PR.
- Wenn ein Issue komplex ist, bleiben Teilfragen trotzdem im selben Thread.
