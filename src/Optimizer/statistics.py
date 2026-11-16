"""Statistika opakovanych behu (TESTING-OPTIMIZATION §4.6, §5.5).

Median + IQR (odolne vuci odlehlym), Mann-Whitney U (neparametricky test,
jednostranny H1: kandidat lepsi = nizsi TotalScore) exaktni pro mala n
(permutacni, s midranks pri shodach), normalni aproximace pro vetsi n.
Pri n < 4 (exaktni p nemuze klesnout pod 0.05) se pouzije pravidlo
prumer +- rozptyl (neprekryv pasem mean+-std). Pouze stdlib.
"""

import itertools
import math


def median(values):
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ValueError("median z prazdneho seznamu")
    mid = n // 2
    if n % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def mean(values):
    if not values:
        raise ValueError("mean z prazdneho seznamu")
    return sum(values) / len(values)


def stdev_sample(values):
    n = len(values)
    if n < 2:
        return 0.0
    avg = mean(values)
    return math.sqrt(sum((v - avg) ** 2 for v in values) / (n - 1))


def iqr(values):
    """Mezikvartilove rozpeti (hinges: median dolni/horni poloviny)."""
    ordered = sorted(values)
    n = len(ordered)
    if n < 2:
        return 0.0
    mid = n // 2
    lower = ordered[:mid]
    upper = ordered[mid:] if n % 2 == 0 else ordered[mid + 1:]
    if not lower or not upper:
        return 0.0
    return median(upper) - median(lower)


def describe(samples):
    """Souhrn distribuce opakovani: n, median, mean, stdev, iqr."""
    samples = [float(v) for v in samples]
    return {
        "n": len(samples),
        "median": median(samples),
        "mean": mean(samples),
        "stdev": stdev_sample(samples),
        "iqr": iqr(samples),
    }


def _midranks(pooled):
    """Prumerna poradi pro setridene hodnoty (shody = midrank)."""
    ranks = [0.0] * len(pooled)
    i = 0
    while i < len(pooled):
        j = i
        while j + 1 < len(pooled) and pooled[j + 1] == pooled[i]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0  # poradi od 1
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1
    return ranks


def mann_whitney_less(x, y):
    """Mann-Whitney U, H1: x stochasticky nizsi nez y. Vraci (U_obs, p_value).

    U_obs = rank_sum(x) - n*(n+1)/2 (nizsi = lepsi). Exaktni jednostranne p
    permutaci kombinaci (midranks pri shodach); nad 20000 kombinaci normalni
    aproximace s korekci na shody a kontinuitu.
    """
    x = [float(v) for v in x]
    y = [float(v) for v in y]
    n, m = len(x), len(y)
    if n == 0 or m == 0:
        raise ValueError("Mann-Whitney vyzaduje neprazdne vzorky")
    pooled = sorted(x + y)
    ranks = _midranks(pooled)
    # Prirad poradi: prvnich n nejmensich... pozor, potrebujeme mapovani
    # hodnot -> poradi; pri shodach pouzijeme mult mnozinu ranku.
    # Jednodussi korektni postup: oznacime prvky a permutujeme indexy.
    items = [(v, 0) for v in x] + [(v, 1) for v in y]
    items_sorted = sorted(range(n + m), key=lambda i: pooled[i])
    # rank_sum(x): secti ranky pozic obsazenych skupinou 0 v serazenem poradi.
    # Rekonstrukce: seradime (hodnota, skupina) a priradime midranks.
    order = sorted(range(n + m), key=lambda i: (x + y)[i])
    rank_of_pos = {}
    i = 0
    vals = x + y
    while i < n + m:
        j = i
        while j + 1 < n + m and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            rank_of_pos[order[k]] = avg_rank
        i = j + 1
    rank_sum_x = sum(rank_of_pos[i] for i in range(n))
    u_obs = rank_sum_x - n * (n + 1) / 2.0

    total_comb = math.comb(n + m, n)
    if total_comb <= 20000:
        # Exaktni: podil kombinaci s U <= U_obs (shody = konzervativne <=).
        count = 0
        all_ranks = [rank_of_pos[i] for i in order]
        for combo in itertools.combinations(range(n + m), n):
            s = sum(all_ranks[i] for i in combo)
            if s - n * (n + 1) / 2.0 <= u_obs + 1e-12:
                count += 1
        return u_obs, count / total_comb
    # Normalni aproximace s korekci na shody.
    mu = n * m / 2.0
    # Korekce rozptylu na shody (t = velikosti skupin shod).
    tie_sum = 0.0
    i = 0
    while i < n + m:
        j = i
        while j + 1 < n + m and pooled[j + 1] == pooled[i]:
            j += 1
        t = j - i + 1
        tie_sum += t ** 3 - t
        i = j + 1
    n_tot = n + m
    var = n * m / 12.0 * ((n_tot + 1) - tie_sum / (n_tot * (n_tot - 1)))
    if var <= 0:
        return u_obs, 1.0
    z = (u_obs - mu + 0.5) / math.sqrt(var)  # korekce na kontinuitu
    return u_obs, 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def means_separated(x, y):
    """Pravidlo prumer +- rozptyl pro mala n: pasma (mean+-std) se neprekrývaji
    a kandidat ma nizsi prumer. Vraci (odděleno, mezera)."""
    mx, my = mean([float(v) for v in x]), mean([float(v) for v in y])
    sx, sy = stdev_sample([float(v) for v in x]), stdev_sample([float(v) for v in y])
    gap = (my - sy) - (mx + sx)
    return (gap > 0.0 and mx < my), gap
