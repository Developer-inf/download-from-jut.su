import os
import sys
import time
import requests
import bs4
import multiprocessing as mp

MAX_LEN = 23

load_symbs = {
    '\\': '|',
    '|': '/',
    '/': '-',
    '-': '\\',
}


headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
}


def check_args() -> None:
    if len(sys.argv) < 2:
        print(f'Usage: python jutsu.py <dir to download> [-f filename with url]')
        exit(1)


def change_directory() -> None:
    if not os.path.isdir(sys.argv[1]):
        os.mkdir(sys.argv[1])
    os.chdir(sys.argv[1])


def get_main_page_url() -> str:
    if 2 < len(sys.argv) < 5 and sys.argv[2] == '-f':
        with open(sys.argv[3], 'r') as f:
            url = f.read()
        return url
    return input("Enter main page url: ").strip()


def make_url_file(name: str, url: str) -> None:
    if not os.path.exists(f'url_{name}'):
        with open(f'url_{name}', 'w') as f:
            f.write(url)


def get_videos_urls(url: str) -> list[str]:
    try:
        page = requests.get(url=url, headers=headers, allow_redirects=True)
    except Exception:
        print(f'Unreachable link {url}')
        exit(2)
    soup = bs4.BeautifulSoup(page.content, 'lxml')
    
    tags = soup.find_all('a', attrs={ 'class': 'short-btn'} )
    urls: list[str] = [x['href'] for x in tags]
    
    for pos, tag in enumerate(tags, start=1):
        print(f'{pos:<3} | {tag.text}:    https://jut.su{tag["href"]}')
    
    title = " ".join(soup.find("h1", attrs={ "class": "header_video" }).text.split()[1:])
    title = translate_name(title)
    make_url_file(title, url)
    
    return urls


def get_options() -> tuple[int, int]:
    opts: str = input("Enter numbers [from] [to] for choose series or nothing to download all: ")
    
    match opts.split():
        case x,:
            opts = (int(x), 10**5)
        case x, y:
            opts = (int(x), int(y))
        case _:
            opts = (0, 10**5)
    
    return opts


def get_source_urls_with_name(urls: list[str], opts: tuple[int, int]):
    beg, end = opts
    beg = 1 if beg-1 < 0 else beg
    urls_with_names: dict[str, str] = {}
    
    urls = urls[beg-1:end]
    
    res = []
    with mp.Pool(mp.cpu_count()) as pl:
        for url in urls:
            res.append(pl.apply_async(requests.get, kwds={'url': f'https://jut.su{url}', 'headers': headers}))
        
        pages = []
        for page in res:
            pages.append(page.get())
    
    for page in pages:
        soup = bs4.BeautifulSoup(page.content, 'lxml')
        name = ' '.join(soup.find('span', attrs={ 'itemprop': 'name' }).text.split(' ')[1:])
        sources = soup.find_all('source')
        found = False
        for tag in sources:
            if tag['res'] in ('720', '480', '360'):
                found = True
                res = tag['res']
                source = tag['src']
                break
        if not found:
            print(f"\r-Video source not found  ")
            continue
        name += f"_{res}.mp4"
        urls_with_names[name] = f'{source}'
    
    return urls_with_names


def translate_name(name: str) -> str:
    rus_eng = {
        'я': 'ya', 'ч': 'ch', 'с': 's',  'м': 'm',  'и': 'i',   'т': 't',
        'ь': '\'', 'б': 'b',  'ю': 'yu', 'ф': 'f',  'ы': 'y',   'в': 'v',
        'а': 'a',  'п': 'p',  'р': 'r',  'о': 'o',  'л': 'l',   'д': 'd',
        'ж': 'zh', 'э': 'a',  'й': 'y',  'ц': 'c',  'у': 'u',   'к': 'k',
        'е': 'e',  'н': 'n',  'г': 'g',  'ш': 'sh', 'щ': 'sch', 'з': 'z',
        'х': 'h',  'ъ': '',   ' ': '_'
    }
    
    text = ''
    for ch in name:
        if ch.lower() not in rus_eng:
            text += ch
            continue
        text += rus_eng[ch.lower()]
    
    return text


def translate_names(names: dict[str, str]) -> dict[str, str]:
    res = {}

    for name in names:
        text = translate_name(name)
        res[text] = names[name]

    return res


def download_video(url: str, filename: str) -> None:
    with requests.get(url=url, headers=headers, stream=True) as r:
        r.raise_for_status()
        
        if os.path.exists(filename):
            print(f'\r{filename} already exists')
            return
        
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024): # 1Mb
                f.write(chunk)
    
    print(f'\r{filename} successfully downloaded')


def load_animation():
    symb = '-'
    while True:
        print(f'\r{symb} downloading videos...', end='')
        symb = load_symbs[symb]
        time.sleep(0.3)


def download_videos(urls: dict[str, str]) -> None:
    with mp.Pool(len(urls)) as pl:
        animation = mp.Process(target=load_animation)
        animation.start()
        tasks = [pl.apply_async(download_video, (url, fname)) for fname, url in urls.items()]
        
        for task in tasks:
            task.get()
        
        animation.kill()


def main(*args, **kwargs):
    try:
        check_args()
        main_url: str = get_main_page_url()
        change_directory()
        urls: list[str] = get_videos_urls(main_url)
        options: tuple(int, int) = get_options()
        source_urls_with_name: dict[str, str] = get_source_urls_with_name(urls, options)
        source_urls_with_name = translate_names(source_urls_with_name)
        download_videos(source_urls_with_name)
        print(f'\rAll videos Successfully downloaded!')
        exit(0)
    except KeyboardInterrupt:
        print(f'\rApp was closed by KeyboardInterrupt (ctrl+C)')
    except Exception:
        print(f'\rUnknown exception{" " * 10}')


if __name__ == "__main__":
    main()