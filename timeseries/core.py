# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/81_timeseries_core.ipynb (unless otherwise specified).

__all__ = ['test_eq_tensor', 'TensorTS', 'ToTensorTS', 'TSBlock', 'get_min_max', 'get_mean_std', 'Standardize',
           'Normalize', 'default_show_batch', 'lbl_dict', 'TSDataLoaders', 'get_n_channels', 'Ranger', 'ts_learner']

# Cell
from fastai2.basics import *

# Cell
from .data import *
from .models.inception_time import *

# Cell
from fastai2.vision.data import get_grid
from fastai2.learner import *
from fastai2.metrics import *
from fastai2.optimizer import *
from fastai2.callback.hook import *
from fastai2.callback.schedule import *
from fastai2.callback.progress import *
# from fastai2.callback.mixup import *

# Cell
def test_eq_tensor(a,b):
    "assert tensor equality"
    assert (a-b).pow(2).sum() <= 1e-10, f"{a}\n{b}"

# Cell
class TensorTS(TensorBase):
    "Transform a 2D `numpy.ndarray` into a `Tensor`"
    def show(self, ctx=None, title=None, chs=None, leg=True, **kwargs):
        "Display timeseries plots for all selected channels list `chs`"
        if ctx is None: fig, ctx = plt.subplots()
        t = range(self.shape[1])
        chs_max = max(chs) if chs else 0
        channels = chs if (chs and (chs_max < self.shape[0])) else range(self.shape[0])
        for ch in channels:
            ctx.plot(t, self[ch], label='ch'+str(ch))
        if leg: ctx.legend(loc='upper right', ncol=2, framealpha=0.5)
        if title: ctx.set_title(title)

# Cell
class ToTensorTS(ItemTransform):
    # "x : 2D numpy array"
    def encodes(self, x): return TensorTS(x)
    def decodes(self, x): return x.numpy()

# Cell
def TSBlock():
    "`TransformBlock` for timeseries : Transform np array to TensorTS type"
    return TransformBlock(type_tfms=ToTensorTS())

# Cell
def get_min_max(train, scale_subtype='all_samples'):
    "get_mean_std is only needed when we want to normalize timeseries tensors using ALL SAMPLES statistics"
    "For SINGLE SAMPLE normalization (Standardization), please check out both `class Normalize` and `class Standardize`"
    "Exampe NATOPS => shape = [360, 24, 51]"

    "returns a tensor of a shape of [n_channels, sequence_length]. For NATOPS it is [24, 51]"
    "This way is more effectient because we do not need to broadcast every time when we will normalize (scale) a timeseries tensor"
    if len(train) <= 0:
        return None,None
    else:
        n_channels = train[0].shape[0]
        sequence_length = train[0].shape[1]

    #Exampe NATOPS => shape = [360, 24, 51]
    # 'all_samples' => returns (mean , std) as scalars
    if scale_subtype == 'all_samples':
        train_min = train.min()
        train_max = train.max()
        min = torch.tensor(train_min).expand(n_channels, sequence_length)
        max = torch.tensor(train_max).expand(n_channels, sequence_length)
    # 'per_channel' => returns (mean , std) with each a shape = [n_channels] => For NATOPS [24]
    elif scale_subtype == 'all_samples_per_channel':
        train_min = train.min(axis=(0, 2))
        train_max = train.max(axis=(0, 2))
        min = torch.tensor(train_min).unsqueeze(1).repeat(1, sequence_length)
        max = torch.tensor(train_max).unsqueeze(1).repeat(1, sequence_length)
    else:
        print(f'In {scale_type} : ***** Please, select a valid  scale_subtype ***** - You passed : {scale_subtype}')
        return None,None
    # returns a tensor of a shape of [n_channels, sequence_length]. For NATOPS it's [24, 51]
    # This way is more effectient because we do not need to broadcast every time we normalize (scale) a timeseries tensor
    return min, max

# Cell
def get_mean_std(train, scale_subtype='all_samples'):
    "get_mean_std is only needed when we want to normalize timeseries tensors using ALL SAMPLES statistics"
    "For SINGLE SAMPLE normalization (Standardization), please check out both `class Normalize` and `class Standardize`"
    "Exampe NATOPS => shape = [360, 24, 51]"

    "returns a tensor of a shape of [n_channels, sequence_length]. For NATOPS it is [24, 51]"
    "This way is more effectient because we do not need to broadcast every time when we will normalize (scale) a timeseries tensor"
    if len(train) <= 0:
        return None,None
    else:
        n_channels = train[0].shape[0]
        sequence_length = train[0].shape[1]
        # print(x.shape, sequence_length)

    #Exampe NATOPS => shape = [360, 24, 51]
    # 'all_samples' => returns (mean , std) as scalars
    if scale_subtype == 'all_samples':
        train_mean = train.mean()
        train_std = train.std()
        mean = torch.tensor(train_mean).expand(n_channels, sequence_length)
        std  = torch.tensor(train_std).expand(n_channels, sequence_length)
    # 'per_channel' => returns (mean , std) with each a shape = [n_channels] => For NATOPS [24]
    elif scale_subtype == 'all_samples_per_channel':
        train_mean = train.mean(axis=(0, 2))
        train_std = train.std(axis=(0, 2))
        mean = torch.tensor(train_mean).unsqueeze(1).repeat(1, sequence_length)
        std  = torch.tensor(train_std).unsqueeze(1).repeat(1, sequence_length)
    else:
        print(f'In {scale_type} : ***** Please, select a valid  scale_subtype ***** - You passed : {scale_subtype}')
        return None,None
    return mean, std

# Cell
@docs
class Standardize(Transform):
    "In Timerseries Lingo, Standardize means normalize the timeseries (counter-intuitive)"
    "Scale timeserie x `TensorTS` using the mean and standard deviation"
    order=99
    def __init__(self, mean=None, std=None, scale_subtype='per_sample_per_channel', cuda=True):
        self.scale_subtype = scale_subtype

        f = to_device if cuda else noop
        if mean is not None:
            self.mean = f(mean)
        if std is not None:
           self.std = f(std)

    # 'all_samples' => returns (mean , std) with each a shape = [1, 1, 1]
    # 'per_channel' => returns (mean , std) with each a shape = [1, 24, 1]

    def encodes(self, x:TensorTS):
        #print('Standardize - encodes')
        # if self.scale_subtype == 'per_sample' or per_sample_per_channel, compute (mean, std) of the current x:TensorTS (sample)
        if self.scale_subtype == 'per_sample':
            self.mean = x.mean(axis=(0,1), keepdims=True)
            self.std = x.std(axis=(0,1), keepdims=True) # + 1e-7 like fastai
        elif self.scale_subtype == 'per_sample_per_channel':
            # print('per_sample_per_channel')
            self.mean = x.mean(axis=(1), keepdims=True)
            self.std = x.std(axis=(1), keepdims=True)  # + 1e-7 like fastai
        return (x-self.mean) / self.std

    def decodes(self, x:TensorTS):
        f = to_cpu if x.device.type=='cpu' else noop
        return (x*f(self.std) + f(self.mean))

    _docs=dict(encodes="Scale timeserie x `TensorTS` using the `mean` and `standard deviation`",
    decodes="Reverse the scaling transform. Get the orignal timeserie values")

# Cell
@docs
class Normalize(Transform):
    "In Timerseries Lingo, Normalize means scale the timeseries (counter-intuitive) between its min and max values"
    "Scale timeserie x `TensorTS` using the min and max values"
    order=99
    def __init__(self, min=None, max=None, scale_subtype='per_sample_per_channel', scale_range=(0, 1), cuda=True):
        self.scale_subtype = scale_subtype
        self.scale_range = scale_range
        f = to_device if cuda else noop
        if min is not None:
            self.min = f(min)
        if max is not None:
           self.max = f(max)

    # 'all_samples' => returns (min , max) with each a shape = [1, 1, 1]
    # 'per_channel' => returns (min , max) with each a shape = [1, 24, 1]
    def encodes(self, x:TensorTS):
        #print('Standardize - encodes')
        # if self.scale_subtype == 'per_sample' or per_sample_per_channel, compute (min, max) of the current x:TensorTS (sample)
        if self.scale_subtype == 'per_sample':
            self.min = TensorTS((torch.min(x)).expand_as(x))
            self.max = TensorTS((torch.max(x)).expand_as(x))
            # self.min = x.min(axis=(0,1), keepdim=True).values
            # self.max = x.max(axis=(0,1), keepdim=True).values
        elif self.scale_subtype == 'per_sample_per_channel':
#           print('per_sample_per_channel')
            # self.min = TensorTS(x.min(axis=(1), keepdims=True).values)
            # self.max = TensorTS(x.max(axis=(1), keepdims=True).values)
            self.min = TensorTS(torch.min(x, dim=1, keepdims=True).values)
            self.max = TensorTS(torch.max(x, dim=1, keepdims=True).values)
        return ((x-self.min)/(self.max - self.min))*(self.scale_range[1] - self.scale_range[0]) + self.scale_range[0]


    def decodes(self, x:TensorTS):
        f = to_cpu if x.device.type=='cpu' else noop
        x_orig = ((x-self.scale_range[0])/(self.scale_range[1] - self.scale_range[0]))*(self.max - self.min) + self.min
        return f(x_orig)

    _docs=dict(encodes="Scale timeserie x `TensorTS` using the `min` and `max` values",
    decodes="Reverse the scaling transform. Get the orignal timeserie values")

# Cell
def default_show_batch(x, y, samples, ctxs=None, max_n=9, **kwargs):
    if ctxs is None: ctxs = Inf.nones
    ctxs = [b[0].show(ctx=c, title=b[1], **kwargs) for b,c,_ in zip(samples,ctxs,range(max_n))]
    return ctxs

# Cell
@typedispatch
def show_batch(x:TensorTS, y, samples, ctxs=None, max_n=9, nrows=None, ncols=None, figsize=(14,12), **kwargs):
    if ctxs is None: ctxs = get_grid(min(len(samples), max_n), nrows=nrows, ncols=ncols, figsize=figsize)
    ctxs = default_show_batch(x, y, samples, ctxs=ctxs, max_n=max_n, **kwargs)
    return ctxs

# Cell
@typedispatch
def default_show_results(x, y, samples, outs, ctxs=None, max_n=9, figsize=(14,12), **kwargs):
    if ctxs is None: ctxs = Inf.nones
    ctxs = [b[0].show(ctx=c, title=f'{o} / {b[1]}', figsize=figsize, **kwargs) for b,o,c,_ in zip(samples,outs,ctxs,range(max_n))]
    return ctxs

# Cell
@typedispatch
def show_results(x:TensorTS, y, samples, outs, ctxs=None, max_n=9, nrows=None, ncols=None, figsize=(14,12), **kwargs):
    if ctxs is None: ctxs = get_grid(min(len(samples), max_n), nrows=nrows, ncols=ncols, add_vert=1, figsize=figsize)
    # outs = [('6.0',),('2.0',)]
    outs = [detuplify(o) for o in outs]
    # outs = ['6.0', '2.0']

    ctxs = default_show_results(x, y, samples, outs, ctxs=ctxs, max_n=max_n, figsize=figsize, **kwargs)
    return ctxs

# Cell
lbl_dict = dict([
    ('1.0', 'I have command'),
    ('2.0', 'All clear'),
    ('3.0', 'Not clear'),
    ('4.0', 'Spread wings'),
    ('5.0', 'Fold wings'),
    ('6.0', 'Lock wings')]
)

# Cell
class TSDataLoaders(DataLoaders):
    @classmethod
    @delegates(DataLoaders.from_dblock)
    def from_files(cls, fnames,  path='.', valid_pct=0.2, seed=None, item_tfms=None, batch_tfms=None, lbl_dict=None, **kwargs):
        "Create timeseries dataloaders from a list of timeseries files in `fnames` in `path`."
        # if getters is None: getters = L(ItemGetter(i) for i in range(2 if blocks is None else len(L(blocks))))
        if seed is None: seed = 42
        getters = [ItemGetter(0), ItemGetter(1)] if lbl_dict is None else [ItemGetter(0), [ItemGetter(1), lbl_dict.get]]
        dblock = DataBlock(blocks=(TSBlock, CategoryBlock),
                           get_items=get_ts_items,
                           getters=getters,
                           splitter=RandomSplitter(seed=seed),
                           item_tfms=item_tfms,
                           batch_tfms=batch_tfms)

        return cls.from_dblock(dblock, fnames, path, **kwargs)

# Cell
def get_n_channels(dl: DataLoader):
    return dl.dataset[0][0].shape[0]

# Cell
# opt_func = partial(Adam, lr=3e-3, wd=0.01)
#Or use Ranger
def Ranger(p, lr=slice(3e-3)): return Lookahead(RAdam(p, lr=lr, mom=0.95, wd=0.01))

# Cell
@delegates(Learner.__init__)
# def cnn_learner(dls, arch, loss_func=None, pretrained=True, cut=None, splitter=None,
                # y_range=None, config=None, n_in=3, n_out=None, normalize=True, **kwargs):
def ts_learner(dls, model=None, opt_func=Ranger, loss_func=None, cbs=None, metrics=None, **kwargs):
    "Build a ts learner with default settings if None is passed"
    n_in = get_n_channels(dls.train) # data.n_channels
    n_out= dls.c # Number of classes

    if model is None: model = inception_time(n_in, n_out).to(device=default_device())
    if opt_func is None: opt_func = Ranger
    if loss_func is None: loss_func = LabelSmoothingCrossEntropy()
    if cbs is None: cbs = L(cbs)
    if metrics is None: metrics=accuracy

    learn = Learner(dls, model, opt_func=opt_func, loss_func=loss_func, metrics=metrics, **kwargs)

    return learn