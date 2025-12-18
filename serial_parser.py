import re

class SerialDataParser:
    def __init__(self, tags=None):
        if tags is None:
            self.tags = ["TMP", "HUM", "PRS", "ET", "O3"]
        else:
            self.tags = tags

    def parse(self, raw_data):
        """
        Parsea la cadena cruda de datos y devuelve un dict {tag: valor}
        Retorna None si no hay datos válidos.
        """
        # Verificar trama completa
        match = re.search(r"<(ESP1|ESP2)>(.*?)</\1>", raw_data)
        if not match:
            return None
        esp = match.group(1)
        payload = match.group(2)
        result = {}

        for tag in self.tags:
            m = re.search(rf"<{tag}>(.*?)</{tag}>", payload)
            if m:
                try:
                    result[tag] = float(m.group(1))
                except ValueError:
                    result[tag] = None
            else:
                result[tag] = None

        # Si alguno es None, puedes decidir ignorar:
        if any(v is None for v in result.values()):
            return None
        result["esp"] = esp
        return result
