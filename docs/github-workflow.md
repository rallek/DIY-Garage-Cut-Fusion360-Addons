# GitHub-Arbeitsmodell

Dieses Dokument beschreibt die Arbeitsregeln für Code, Dokumentation und Tickets.

## Ziel

Wir arbeiten nachvollziehbar, klein geschnitten und versionierbar.

## Kernregeln

- Jedes Thema beginnt mit einem GitHub-Issue.
- Jedes Issue hat genau einen eigenen Thread.
- Jedes Issue bekommt genau einen Pull Request.
- Ein Pull Request behandelt nur ein zusammenhängendes Thema.
- `main` bleibt geschützt und wird nur per Pull Request geändert.
- Diskussionen und Entscheidungen laufen zuerst im Issue, nicht verstreut in mehreren Stellen.

## Issue-Struktur

Jedes Issue soll enthalten:

- Ziel
- Kontext
- fachliche Abgrenzung
- technische Notizen
- Akzeptanzkriterien
- offene Fragen

## Pull-Request-Struktur

Jeder PR soll enthalten:

- Verweis auf das zugehörige Issue
- kurze Beschreibung der Änderung
- Hinweise zur Prüfung
- Doku-Änderungen, falls nötig

## Branch-Konvention

Empfohlenes Schema:

```text
codex/issue-<nummer>-<kurzname>
```

## Labels

Für den Start sind diese Label-Gruppen sinnvoll:

- `type:feature`
- `type:bug`
- `type:docs`
- `type:chore`
- `priority:high`
- `priority:medium`
- `priority:low`
- `status:blocked`
- `status:needs-info`

## Milestones

Die erste grobe Einteilung sollte über Meilensteine laufen:

- `V1 - Add-in + Export`
- `V2 - Stabilisierung`
- `V3 - Erweiterung`

## Definition of Done

Ein Issue ist erst erledigt, wenn:

- die Umsetzung fertig ist
- die Doku aktualisiert ist
- eine technische Prüfung vorhanden ist
- der PR gemerged wurde
- das Issue geschlossen werden kann

