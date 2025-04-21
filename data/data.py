import json

data = []
with open("/home/jkp/Téléchargements/instances_dim_test.json") as f:
    for line in f:
        data.append(json.loads(line.strip()))

print(len(data))
# print infos
print(data[::5][:5])
