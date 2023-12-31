
















import threading

import weetest


def Arithmetic(n):
  return n * 3 + 2


def Fib(n):
  if n < 2:
    return 1
  return Fib(n - 1) + Fib(n - 2)


_WORKLOADS = [
    (Arithmetic, 1001),
    (Fib, 10),
]


def _MakeParallelBenchmark(p, work_func, *args):
  

  def Benchmark(b):  
    e = threading.Event()
    def Target():
      e.wait()
      for _ in xrange(b.N / p):
        work_func(*args)
    threads = []
    for _ in xrange(p):
      t = threading.Thread(target=Target)
      t.start()
      threads.append(t)
    b.ResetTimer()
    e.set()
    for t in threads:
      t.join()
  return Benchmark


def _RegisterBenchmarks():
  for p in xrange(1, 13):
    for work_func, arg in _WORKLOADS:
      name = 'Benchmark' + work_func.__name__
      if p > 1:
        name += 'Parallel%s' % p
      globals()[name] = _MakeParallelBenchmark(p, work_func, arg)
_RegisterBenchmarks()


if __name__ == '__main__':
  weetest.RunBenchmarks()
