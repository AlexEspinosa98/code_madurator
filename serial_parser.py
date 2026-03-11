import re


class SerialDataParser:
    FRAME_PATTERN = re.compile(r"<(ESP1|ESP2)>(.*?)</\1>", re.DOTALL)

    def __init__(self, tags=None, max_buffer_size=8192):
        self.tags = tags or ["TMP", "HUM", "PRS", "ET", "O3"]
        self.max_buffer_size = max_buffer_size
        self._buffer = ""

    def _extract_value(self, payload, tag):
        match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", payload, re.DOTALL)
        if not match:
            return None
        value = match.group(1).strip()
        try:
            return float(value)
        except ValueError:
            return None

    def _parse_frame(self, esp, payload, raw_frame):
        result = {"esp": esp, "_raw_frame": raw_frame}
        has_at_least_one_value = False

        for tag in self.tags:
            parsed_value = self._extract_value(payload, tag)
            result[tag] = parsed_value
            if parsed_value is not None:
                has_at_least_one_value = True

        if not has_at_least_one_value:
            return None
        return result

    def feed(self, raw_chunk):
        """
        Recibe fragmentos de texto serial y devuelve una lista de tramas parseadas.
        Maneja tramas concatenadas (<ESP1>...</ESP1><ESP2>...</ESP2>) y tramas partidas.
        """
        if not raw_chunk:
            return []

        self._buffer += raw_chunk
        parsed_frames = []
        last_consumed = 0

        for match in self.FRAME_PATTERN.finditer(self._buffer):
            esp = match.group(1)
            payload = match.group(2)
            raw_frame = match.group(0)
            parsed = self._parse_frame(esp, payload, raw_frame)
            if parsed is not None:
                parsed_frames.append(parsed)
            last_consumed = match.end()

        if last_consumed:
            self._buffer = self._buffer[last_consumed:]

        # Elimina basura antes del inicio de una posible trama válida.
        first_esp_idx = self._buffer.find("<ESP")
        if first_esp_idx > 0:
            self._buffer = self._buffer[first_esp_idx:]

        if len(self._buffer) > self.max_buffer_size:
            self._buffer = self._buffer[-self.max_buffer_size :]

        return parsed_frames

    def parse(self, raw_data):
        """
        Compatibilidad hacia atrás: devuelve la última trama parseada o None.
        """
        parsed_frames = self.feed(raw_data)
        return parsed_frames[-1] if parsed_frames else None
