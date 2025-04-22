import polars as pl
from PIL import Image
import io

df = pl.read_parquet('/home/jkp/Téléchargements/zerobench_subquestions-00000-of-00001.parquet')


def display_image():
    first_row = df.row(0, named=True)
    images = first_row['question_images_decoded'] # list of images
    print(type(images), len(images), type(images[0]))
    print(images[0].keys(), len(images[0]['bytes']))
    print(images[0]['bytes'][:30], images[0]['path'])

    # for image in images:
    #     print(image.keys())
    #     image = Image.open(BytesIO(image['bytes']))
    #     image.show()
if __name__ == "__main__":

    tasks = df['question_id'].to_list()
    print(tasks)
    print(df.columns) # ['question_id', 'question_text', 'question_images_decoded', 'question_answer', 'question_images', 'image_attribution']
    print(df.head())
    print(df.row(0, named=True).keys())
    display_image()

# holy_grail = pl.read_ndjson('/mnt/home/jkp/hack/tmp/MetaGPT/counting_zero.jsonl')

# print(holy_grail.head())

def merge_images_side_by_side(images):
    # Calculate total width and maximum height
    total_width = sum(img.width for img in images)
    max_height = max(img.height for img in images)
    
    # Create a new image with the calculated size and a white background
    new_img = Image.new('RGB', (total_width, max_height), (255, 255, 255))
    
    # Paste each image side by side
    x = 0
    for img in images:
        new_img.paste(img, (x, 0))
        x += img.width
    
    return new_img

def get_task_data(task_id):
    filtered_df = df.filter(pl.col('question_id') == task_id)
    
    assert filtered_df.height == 1, f"Task ID {task_id} not found or duplicate."

    row = filtered_df.row(0, named=True)

    images = [Image.open(io.BytesIO(x['bytes'])) for x in row['question_images_decoded']]
    
    # assert len(images) == 1, f"Task ID {task_id} does not have exactly one image."
    
    # image_data = images[0]['bytes']
    row['image'] = merge_images_side_by_side(images)
    row['question'] = row['question_text']
    
    return row