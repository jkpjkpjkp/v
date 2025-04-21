from PIL import Image

class Pos:
    x: int # w
    y: int # h
    def pil(self) -> tuple[int, int]:
        return (self.x, self.y)

def show_cursor(image: Image.Image, pos: Pos) -> Image.Image:
    pass

class Cursor:
    def __call__(self, image: Image.Image, pos: Pos):
        pass