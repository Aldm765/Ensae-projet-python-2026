## Effet des décisions de la BCE

### Les données

Nous avons reconstruit le calendrier des décisions de la BCE à partir de ses pages annuelles de politique monétaire, de 2000 à 2025. Comme ces pages mêlent les décisions, les déclarations et les comptes rendus de réunion, nous n'avons gardé que les communiqués intitulés « Monetary policy decisions », ce qui donne 293 dates. Leur rythme varie au cours de la période, puisqu'on compte deux décisions par mois en 2000 et 2001, environ une par mois de 2002 à 2014, puis huit par an depuis 2015.

Nous avons ensuite ajouté la variation du taux de dépôt, tirée de l'API de la BCE. Cette série date chaque changement à son entrée en vigueur, souvent six jours après la décision, si bien que nous attribuons chaque changement à la dernière décision qui le précède. Le 8 octobre 2008 demande un traitement particulier, car le taux de dépôt baisse de 0,50 point ce jour-là puis remonte de 0,50 point le lendemain, lorsque la BCE resserre l'écart entre ses taux. Nous retenons la baisse, sans quoi cette décision d'urgence apparaîtrait comme une absence de changement. Au total, 56 décisions modifient le taux de dépôt et trois autres baissent uniquement le taux principal, le 7 mai 2009, le 2 mai 2013 et le 7 novembre 2013. Nous comptons ces 59 décisions comme des changements de taux. Deux réunions se sont tenues hors calendrier, le 17 septembre 2001 et le 8 octobre 2008.

Le jour de réaction dépend de l'heure de l'annonce. La BCE publie ses décisions à 13h45, puis à 14h15 depuis juillet 2022, donc pendant la séance de Paris et avant l'ouverture de New York. Nous mesurons par conséquent la réaction du CAC 40 et du S&P 500 le jour même. Comme la Bourse de Tokyo est déjà fermée à cette heure, nous regardons le Nikkei à la séance suivante.

### L'effet sur le CAC 40

Le jour de la décision, la volatilité du CAC 40 dépasse de 23 % celle des jours témoins (ratio de 1,23, p < 0,001). L'écart se réduit à 10 % le lendemain, puis la volatilité passe 9 % sous son niveau habituel deux séances après la décision. Ces trois écarts restent significatifs après une correction de Bonferroni sur les 33 tests de la figure.

La hausse est plus forte quand la BCE modifie ses taux, puisqu'elle atteint 44 % pour les 59 décisions avec changement contre 15 % pour les 234 décisions sans changement, et cet écart entre les deux groupes est significatif (p = 0,0005). Le marché réagit donc même lorsque les taux ne bougent pas, mais nos données quotidiennes ne permettent pas de dire si cette réaction vient du communiqué ou de la conférence de presse. Le résultat ne dépend pas des réunions bimensuelles du début de la période, car le ratio reste à 1,23 lorsqu'on retire les années 2000 et 2001. Il ne dépend pas non plus de la mesure de volatilité, puisque l'estimateur de Garman-Klass, qui utilise aussi l'ouverture et la clôture, donne un ratio de 1,22.

### L'effet sur les États-Unis et l'Asie

Le S&P 500 affiche un ratio de 1,08 le jour de la décision (p = 0,013), sur 292 séances parce que Wall Street était fermée le 13 septembre 2001. Ce résultat reste fragile, car il ne résiste pas à la correction des tests multiples et cesse d'être significatif lorsqu'on retire les années 2000 et 2001, le ratio tombant alors à 1,06 (p = 0,08). L'estimateur de Garman-Klass donne lui aussi un effet plus faible, de 1,06 (p = 0,04). De même, l'écart entre les décisions avec changement (1,17) et sans changement (1,03) n'est pas significatif (p = 0,07). Nous ne pouvons donc pas conclure à un effet établi de la BCE sur la volatilité américaine.

Le Nikkei ne réagit pas à la séance suivante, avec un ratio de 0,99 (p = 0,77), et ce constat vaut aussi bien pour les décisions avec changement que sans changement. Le S&P 500 et le Nikkei présentent bien un pic quatre séances après la décision, mais nous ne l'attribuons pas à la BCE, parce que rien ne justifie une réaction aussi tardive et que d'autres annonces peuvent tomber ces jours-là.
