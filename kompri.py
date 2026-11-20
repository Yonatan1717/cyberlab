
import sys

file_to_compress = sys.argv[1]


map_char_to_count = {}

with open(file_to_compress, 'r') as file:
    for line in file:
        for char in line:
            if char in map_char_to_count:
                map_char_to_count[char] += 1
            else:
                map_char_to_count[char] = 1

total_chars = sum(map_char_to_count.values())

map_char_to_probability = {}
for char, count in map_char_to_count.items():
    map_char_to_probability[char] = count / total_chars

for char, probability in map_char_to_probability.items():
    print(f"Character: {char}, Probability: {probability}")


sorted_map = dict(sorted(map_char_to_probability.items(), key=lambda x:x[1],reverse=True))
print(sorted_map)


huffman_codes = {}


