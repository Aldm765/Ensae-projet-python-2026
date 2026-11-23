## Effet des décisions de la Fed

### Les données

Nous avons récupéré les dates des décisions du FOMC de 2000 à 2025 par scraping du site de la Fed : la page du calendrier pour 2021-2025, et une page d'archive par année pour 2000-2020. Chaque réunion dure deux jours ; nous retenons le second, jour de l'annonce.

Nous obtenons 207 réunions prévues, soit 8 par an. Deux anomalies ont été traitées : un doublon en septembre 2003 (réunion comptée le 15 et le 16), et l'année 2020, qui n'en compte que 7 car la réunion de mars a été annulée et remplacée par deux réunions d'urgence au début du Covid.

Le taux directeur, téléchargé via l'API FRED, donne le sens de chaque décision : sur les 214 décisions retenues, 140 laissent le taux inchangé. Il sert aussi à trier les réunions d'urgence : sur 27, nous ne gardons que les 7 où le taux a réellement changé, comme le 17 septembre 2001 ou le 16 mars 2020.

### L'effet sur les marchés américains

La Fed annonce ses décisions à 14h à New York : le S&P 500 réagit donc le jour même. Ce jour-là, sa volatilité est 23 % plus forte que lors d'un jour témoin (ratio de 1,23, p-value inférieure à 0,001). L'effet est donc net et significatif.

Il dure environ deux jours : la volatilité reste élevée le lendemain (ratio de 1,18), puis revient à la normale. À l'inverse, la veille de l'annonce, elle est plus faible que d'habitude (ratio de 0,94) : les marchés attendent la décision.

Le VIX, qui mesure la volatilité attendue par les marchés, monte légèrement dans les jours qui précèdent l'annonce, puis baisse de 1,7 % le jour même. La décision semble lever une incertitude : les marchés s'agitent sur le moment, mais anticipent ensuite des semaines plus calmes.

### L'effet sur l'Europe et l'Asie

À 14h à New York, il est 20h à Paris et la nuit à Tokyo : le CAC 40 et le Nikkei sont fermés et ne peuvent réagir que le lendemain. Ce jour-là, la volatilité du CAC 40 est 13 % plus forte que lors d'un jour témoin (p-value inférieure à 0,001), et celle du Nikkei 11 % plus forte (p-value de 0,001).

Le choc se transmet donc bien hors des États-Unis, mais en s'atténuant : l'effet est environ deux fois plus faible en Europe et en Asie qu'à New York.

### Contrôle : réunions prévues et urgences

Les 7 décisions d'urgence sont des baisses de taux surprises, prises entre deux réunions, souvent en pleine crise. Leur effet est beaucoup plus fort : la volatilité fait plus que doubler le jour de la réaction sur le S&P 500 (ratio de 2,46) et sur le CAC 40 (2,47), contre 1,23 et 1,13 pour les réunions prévues. Sur le Nikkei, l'effet (1,41) est à la limite de la significativité (p-value de 0,06). Ce contraste confirme que c'est l'effet de surprise qui fait réagir les marchés.

### Limites

- Les données sont quotidiennes : on mesure l'effet au jour près, pas à la minute.
- Le jour d'une réunion, d'autres nouvelles peuvent aussi tomber : on ne prouve pas que l'annonce cause seule la volatilité. C'est particulièrement vrai pour les urgences, décidées en pleine crise (11 septembre 2001, Covid).
- Le sens de la décision ne mesure pas la surprise : la plupart des décisions sont anticipées par les marchés.
- Les urgences sont datées au jour où le taux change dans FRED. Pour celle de mars 2020, ce jour (le 4) suit d'un jour l'annonce (le 3).
- Avec seulement 7 urgences, le contrôle reste fragile, même si les écarts sont significatifs.
- Nos dates n'ont pas été comparées à une source externe ; elles ont été contrôlées par le nombre de réunions par an et par des vérifications manuelles.