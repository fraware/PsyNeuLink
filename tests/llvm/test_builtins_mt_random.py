import ctypes
import numpy as np
import pytest
import random

from psyneulink.core import llvm as pnlvm

SEED = 0

@pytest.mark.benchmark(group="Mersenne Twister integer PRNG")
@pytest.mark.parametrize('mode', ['Python', 'numpy',
                                  pytest.param('LLVM', marks=pytest.mark.llvm),
                                  pytest.helpers.cuda_param('PTX')])
def test_random_int(benchmark, mode):
    res = []
    if mode == 'Python':
        state = random.Random(SEED)
        def f():
            return state.randrange(0xffffffff)
    elif mode == 'numpy':
        # Numpy promotes elements to int64
        state = np.random.RandomState([SEED])
        def f():
            return state.randint(0xffffffff, dtype=np.int64)
    elif mode == 'LLVM':
        init_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_init')
        state = init_fun.byref_arg_types[0]()
        init_fun(state, SEED)

        gen_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_int32')
        out = ctypes.c_longlong()
        def f():
            gen_fun(state, out)
            return out.value
    elif mode == 'PTX':
        init_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_init')
        state_size = ctypes.sizeof(init_fun.byref_arg_types[0])
        gpu_state = pnlvm.jit_engine.pycuda.driver.mem_alloc(state_size)
        init_fun.cuda_call(gpu_state, np.int32(SEED))

        gen_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_int32')
        out = np.asarray([0], dtype=np.int64)
        gpu_out = pnlvm.jit_engine.pycuda.driver.Out(out)
        def f():
            gen_fun.cuda_call(gpu_state, gpu_out)
            return out[0]
    else:
        assert False, "Unknown mode: {}".format(mode)

    res = [f(), f()]
    assert np.allclose(res, [3626764237, 1654615998])
    benchmark(f)


@pytest.mark.benchmark(group="Mersenne Twister floating point PRNG")
@pytest.mark.parametrize('mode', ['Python', 'numpy',
                                  pytest.param('LLVM', marks=pytest.mark.llvm),
                                  pytest.helpers.cuda_param('PTX')])
def test_random_float(benchmark, mode):
    res = []
    if mode == 'Python':
        # Python treats every seed as array
        state = random.Random(SEED)
        def f():
            return state.random()
    elif mode == 'numpy':
        # numpy promotes elements to int64
        state = np.random.RandomState([SEED])
        def f():
            return state.random_sample()
    elif mode == 'LLVM':
        init_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_init')
        state = init_fun.byref_arg_types[0]()
        init_fun(state, SEED)

        gen_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_double')
        out = gen_fun.byref_arg_types[1]()
        def f():
            gen_fun(state, out)
            return out.value
    elif mode == 'PTX':
        init_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_init')
        state_size = ctypes.sizeof(init_fun.byref_arg_types[0])
        gpu_state = pnlvm.jit_engine.pycuda.driver.mem_alloc(state_size)
        init_fun.cuda_call(gpu_state, np.int32(SEED))

        gen_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_double')
        out = np.asfarray([0.0], dtype=np.dtype(gen_fun.byref_arg_types[1]))
        gpu_out = pnlvm.jit_engine.pycuda.driver.Out(out)
        def f():
            gen_fun.cuda_call(gpu_state, gpu_out)
            return out[0]
    else:
        assert False, "Unknown mode: {}".format(mode)

    res = [f(), f()]
    assert np.allclose(res, [0.8444218515250481, 0.7579544029403025])
    benchmark(f)


@pytest.mark.benchmark(group="Marsenne Twister Normal distribution")
@pytest.mark.parametrize('mode', ['numpy',
                                  pytest.param('LLVM', marks=pytest.mark.llvm),
                                  pytest.helpers.cuda_param('PTX')])
# Python uses different algorithm so skip it in this test
def test_random_normal(benchmark, mode):
    if mode == 'numpy':
        # numpy promotes elements to int64
        state = np.random.RandomState([SEED])
        def f():
            return state.normal()
    elif mode == 'LLVM':
        init_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_init')
        state = init_fun.byref_arg_types[0]()
        init_fun(state, SEED)

        gen_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_normal')
        out = gen_fun.byref_arg_types[1]()
        def f():
            gen_fun(state, out)
            return out.value
    elif mode == 'PTX':
        init_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_init')
        state_size = ctypes.sizeof(init_fun.byref_arg_types[0])
        gpu_state = pnlvm.jit_engine.pycuda.driver.mem_alloc(state_size)
        init_fun.cuda_call(gpu_state, np.int32(SEED))

        gen_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_normal')
        out = np.asfarray([0.0], dtype=np.dtype(gen_fun.byref_arg_types[1]))
        gpu_out = pnlvm.jit_engine.pycuda.driver.Out(out)
        def f():
            gen_fun.cuda_call(gpu_state, gpu_out)
            return out[0]
    else:
        assert False, "Unknown mode: {}".format(mode)

    res = [f(), f()]
    assert np.allclose(res, [0.4644982638709743, 0.6202001216069017])
    benchmark(f)

@pytest.mark.benchmark(group="Marsenne Twister Binomial distribution")
@pytest.mark.parametrize('mode', ['numpy',
                                  pytest.param('LLVM', marks=pytest.mark.llvm),
                                  pytest.helpers.cuda_param('PTX')])
@pytest.mark.parametrize('n', [1])
@pytest.mark.parametrize('p, exp', [
    (0, [0]),
    (0.1, [0x20d00c]),
    (0.33, [0xc224f70d]),
    (0.5, [0xca76f71d]),
    (0.66, [0x3ddb08f2]),
    (0.95, [0xffffbffb]),
    (1, [0xffffffff]),
    ])
# Python uses different algorithm so skip it in this test
def test_random_binomial(benchmark, mode, n, p, exp):
    if mode == 'numpy':
        # numpy promotes elements to int64
        state = np.random.RandomState([SEED])
        def f():
            return state.binomial(n, p)
    elif mode == 'LLVM':
        init_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_init')
        state = init_fun.byref_arg_types[0]()
        init_fun(state, SEED)

        gen_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_binomial')
        c_n = gen_fun.byref_arg_types[1](n)
        c_p = gen_fun.byref_arg_types[2](p)
        c_out = gen_fun.byref_arg_types[-1]()
        def f():
            gen_fun(state, c_n, c_p, c_out)
            return c_out.value
    elif mode == 'PTX':
        init_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_init')
        state_size = ctypes.sizeof(init_fun.byref_arg_types[0])
        gpu_state = pnlvm.jit_engine.pycuda.driver.mem_alloc(state_size)
        init_fun.cuda_call(gpu_state, np.int32(SEED))

        gen_fun = pnlvm.LLVMBinaryFunction.get('__pnl_builtin_mt_rand_binomial')
        gpu_n = pnlvm.jit_engine.pycuda.driver.In(np.array([n], dtype=np.dtype(gen_fun.byref_arg_types[1])))
        gpu_p = pnlvm.jit_engine.pycuda.driver.In(np.array([p], dtype=np.dtype(gen_fun.byref_arg_types[2])))
        out = np.array([0.0], dtype=np.dtype(gen_fun.byref_arg_types[3]))
        gpu_out = pnlvm.jit_engine.pycuda.driver.Out(out)

        def f():
            gen_fun.cuda_call(gpu_state, gpu_n, gpu_p, gpu_out)
            return out[0]
    else:
        assert False, "Unknown mode: {}".format(mode)

    res = [f() for _ in range(32)]
    res = int(''.join(str(x) for x in res), 2)
    assert res == exp[n - 1]
    benchmark(f)
