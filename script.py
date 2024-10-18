from pathlib import Path
from os import system
from os.path import exists
import random
import re
import requests
from bs4 import BeautifulSoup

ANKI_MEDIA = ".local/share/Anki2/User 1/collection.media/"
TREE_URLS = "treeurls.txt"
CSV_PATH = "trees.csv"


class Tree:
    def __init__(self, *args):
        args = args[0]

        self.names = args[0]
        self.binomial = args[1]
        self.blurb = args[2]
        self.family = args[3]
        self.origin = args[4]
        self.headings = args[5]
        self.image_urls = args[6]
        self.url = args[7]

    def name(self):
        return first_upper(self.names[0])

    def other_names(self):
        return ", ".join(self.names[1:])

    def tag_string(self):
        reg = re.compile(r"\W")
        tags = [self.family, first_upper(f"{self.origin} tree")]
        return " ".join([reg.sub("_", tag) for tag in tags])

    def image_filename(self, number):
        reg = re.compile(r"\W")
        name_string = reg.sub("-", self.name().lower())
        return f"tree_{name_string}{number}.jpg"

    def __str__(self):
        max_images = 10
        image_count = 0
        fields = [self.name(), self.url, self.blurb, self.other_names(), self.binomial]
        for cnt in range(max_images):
            if cnt < len(self.image_urls):
                fields.append(self.image_urls[cnt])
                filename = self.image_filename(cnt + 1)
                image_count += 1
                fields.append(f'<img src="{filename}">')
            else:
                fields.append("")
                fields.append("")
        for header in self.headings:
            if header["img_src"]:
                fields.append(header["img_src"])
                filename = self.image_filename(image_count + 1)
                image_count += 1
                fields.append(f'<img src="{filename}">')
            else:
                fields.append("")
                fields.append("")
            if header["desc"]:
                fields.append(header["desc"])
            else:
                fields.append("")
        fields.append(self.tag_string())
        string = ",".join([normalize_csv(field) for field in fields])
        return string

    def download_images(self):
        image_count = 0
        heading_images = [head["img_src"] for head in self.headings]
        for url in self.image_urls + heading_images:
            vert_px = 300
            filename = self.image_filename(image_count + 1)
            path = Path.home() / ANKI_MEDIA / filename
            command = f'ffmpeg -i "{url}" -vf scale=-1:{vert_px} "{path}"'
            if exists(path):
                print(f"Already found: {path}")
            else:
                print(command)
                system(command)
            image_count += 1

    def is_common(self):
        # based on https://www.woodlandtrust.org.uk/blog/2018/12/what-are-the-most-common-trees-in-the-uk/
        common_trees = [
            "alder",
            "beech",
            "english oak",
            "hawthorn",
            "hazel",
            "holly",
            "rowan",
            "silver birch",
            "small-leaved lime",
            "white willow",
        ]
        lower_names = [name.lower() for name in self.names]
        if set(lower_names).intersection(common_trees) == set():
            return False
        return True


def get_page(url):
    # woodlandtrust.org.uk blocks requests with the python-requests user agent
    # string
    headers = {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0"
    }
    html = requests.get(url, headers=headers).text
    return BeautifulSoup(html, "lxml")


def get_tree_urls():
    base_url = "https://www.woodlandtrust.org.uk"
    page = get_page(
        base_url + "/trees-woods-and-wildlife/british-trees/a-z-of-british-trees/"
    )
    urls = [
        link["href"] for link in page.find("section").find_all(class_="excerpt-link")
    ]
    urls = [base_url + url for url in urls]
    with open(TREE_URLS, "w") as file:
        file.writelines([url + "\n" for url in urls])


def random_tree():
    tree_urls = []
    with open(TREE_URLS, "r") as file:
        tree_urls = [url.rstrip() for url in file.readlines()]
    return random.choice(tree_urls)


def random_test(times):
    trees = []
    for _ in range(times):
        tree_url = random_tree()
        reg = re.compile("/([^/]*)/$")
        print(f"{reg.search(tree_url).group(1)}:")
        trees.append(get_info(tree_url))
    return trees


def normalize_image_url(url):
    base_url = "https://www.woodlandtrust.org.uk"
    reg = re.compile(r"(.*)\?")
    return base_url + reg.search(url).group(1)


def find_strong(strong_reg, page):
    reg = re.compile(strong_reg)
    context = str(page.find("strong", text=reg).parent)
    reg = re.compile(rf"<strong>{strong_reg}\W*</strong>[^(<|\w)]*(.*?)<(/p|br/)>")
    try:
        return reg.search(context).group(1)
    except:
        return None


def get_info(url):
    page = get_page(url)

    h3s = [
        {"heading": "Leaves", "img_src": None, "desc": None},
        {"heading": "Flowers", "img_src": None, "desc": None},
        {"heading": "Fruits", "img_src": None, "desc": None},
    ]
    for h3 in h3s:
        if page.find(text=h3["heading"]):
            ancestor = page.find(text=h3["heading"]).parent.parent.parent.parent
            try:
                img_src = ancestor.find("img")["src"]
                h3["img_src"] = normalize_image_url(img_src)
            except:
                h3["img_src"] = None
            h3["desc"] = ancestor.find_all("p")[1].text

    imgs = page.find_all(class_="container-fluid")[0].find_all("img")
    image_urls = []
    for img in imgs:
        try:
            data_lazy = normalize_image_url(img["data-lazy"])
            if data_lazy not in [h3["img_src"] for h3 in h3s]:
                image_urls.append(data_lazy)
        except:
            continue

    common_names = find_strong(r"Common name\(?s?\)?:", page).split(", ")

    binomial = find_strong("Scientific name:", page)

    family = find_strong("Family:", page)

    origin = find_strong("Origin:", page)

    blurb = page.find("main").find("p").text

    return Tree([common_names, binomial, blurb, family, origin, h3s, image_urls, url])


def first_upper(string):
    return string[0:1].upper() + string[1:]


def normalize_csv(string):
    if string is None:
        return '""'
    doubled_quotes = string.replace('"', '""')
    return f'"{doubled_quotes}"'


def write_csv(filename, trees):
    random.shuffle(trees)
    trees.sort(key=lambda tree: tree.is_common(), reverse=True)
    with open(filename, "w") as file:
        file.writelines([f"{str(tree)}\n" for tree in trees])


def download_trees():
    tree_urls = []
    with open(TREE_URLS, "r") as file:
        tree_urls = [url.rstrip() for url in file.readlines()]
    trees = []
    for url in tree_urls:
        print(f"Fetching {url}")
        tree = get_info(url)
        trees.append(tree)
        print("Downloading images...")
        tree.download_images()
    write_csv(CSV_PATH, trees)
