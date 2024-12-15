import threading
import queue
import time
import random

class Collector(threading.Thread):
    def __init__(self, data_queue, collector_id):
        super().__init__()
        self.data_queue = data_queue
        self.collector_id = collector_id
        self.running = True

    def run(self):
        while self.running:
            data = "Make-Sense" if random.random() < 0.15 else "Non-Sense"
            print(f"Collector {self.collector_id} collected: {data}")
            self.data_queue.put(data)
            time.sleep(1)

    def stop(self):
        self.running = False

class Analyzer(threading.Thread):
    def __init__(self, data_queue, result_queue, analyzer_id):
        super().__init__()
        self.data_queue = data_queue
        self.result_queue = result_queue
        self.analyzer_id = analyzer_id
        self.running = True

    def run(self):
        while self.running or not self.data_queue.empty():
            try:
                data = self.data_queue.get(timeout=1)
                if data == "Make-Sense":
                    print(f"Analyzer {self.analyzer_id} counted Make-Sense data.")
                    self.result_queue.put(1)
                else:
                    self.result_queue.put(0)
                self.data_queue.task_done()
                time.sleep(0.5)
            except queue.Empty:
                pass

    def stop(self):
        self.running = False

class Merger(threading.Thread):
    def __init__(self, result_queue):
        super().__init__()
        self.result_queue = result_queue
        self.running = True

    def run(self):
        while self.running:
            total_sense = 0
            time.sleep(60)  
            while not self.result_queue.empty():
                total_sense += self.result_queue.get()
            print(f"\t\t\t\tMerger: Total Make-Sense data in last minute = {total_sense}\n\n\n")
            
    def stop(self):
        self.running = False

def main():
    data_queue = queue.Queue()
    result_queue = queue.Queue()

    collectors = [Collector(data_queue, i) for i in range(10)]
    analyzers = [Analyzer(data_queue, result_queue, i) for i in range(50)]
    merger = Merger(result_queue)

    # Collector ve Analyzer iş parçacıklarını başlatma
    for collector in collectors:
        collector.start()
    for analyzer in analyzers:
        analyzer.start()
    merger.start()

    try:
        time.sleep(300)  # Simülasyonu 5 dakika çalıştırma
    finally:
        # Tüm iş parçacıklarını sonlandırma
        for collector in collectors:
            collector.stop()
        for analyzer in analyzers:
            analyzer.stop()
        merger.stop()

        for collector in collectors:
            collector.join()
        for analyzer in analyzers:
            analyzer.join()
        merger.join()

if __name__ == "__main__":
    main()
