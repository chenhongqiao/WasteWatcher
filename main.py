import os
import multiprocessing as mp
from cv import camera_loop
from save import save_loop
from llm import llm_loop

if __name__ == "__main__":
    save_queue = mp.Queue()
    llm_queue = mp.Queue()

    llm_process = mp.Process(target=llm_loop, args=(llm_queue,))
    llm_process.start()

    save_process = mp.Process(target=save_loop, args=(save_queue,))
    save_process.start()

    camera_process = mp.Process(target=camera_loop, args=(save_queue, llm_queue))
    camera_process.start()
