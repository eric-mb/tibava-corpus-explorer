NAME = "Shot-reverse-shot"

# Shot-reverse-shot: two persons appear in alternating shots, A-B-A-B-A ...
# A shot "shows" the person whose face is detected most often in it
# (`shot.main_person`). Shots without a detected face break the sequence.

MIN_LENGTH = 3  # at least A-B-A; there is no maximum length


def find(video):
    seq = [shot.main_person for shot in video.shots]
    hits = []
    i = 0
    while i < len(seq) - 1:
        a, b = seq[i], seq[i + 1]
        if a is None or b is None or a == b:
            i += 1
            continue
        # extend the run as long as the shots keep alternating between a and b
        j = i + 2
        while j < len(seq) and seq[j] == (a if (j - i) % 2 == 0 else b):
            j += 1
        if j - i >= MIN_LENGTH:
            hits.append(Hit(shots=list(range(i, j)), persons=[a, b]))
            i = j - 1  # the last shot may start the next pattern (e.g. A-B-A-B-C-B-C)
        else:
            i += 1
    return hits
