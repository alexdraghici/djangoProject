# Create your models here.
from channels.db import database_sync_to_async
from django.db import models
from polymorphic.models import PolymorphicModel

# the following lines added:


class ClassPropertyDescriptor(object):

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


class AsyncObjects:
    querryset_methods = ['all', 'filter']
    single_result_methods = ['get', 'count']

    def __init__(self, objects):
        self.objects = objects

    def __getattr__(self, name):
        if name in self.querryset_methods:
            return AsyncObjects(getattr(self.objects, name))
        elif name in self.single_result_methods:
            return database_sync_to_async(getattr(self.objects, name))

    async def get(self, *args, **kwargs):
        return await database_sync_to_async(self.objects.get)(*args, **kwargs)

    async def create(self, *args, **kwargs):
        return await database_sync_to_async(self.objects.create)(*args, **kwargs)

    async def all(self):
        return await database_sync_to_async(list)(self.objects.all())

    async def filter(self, *args, **kwargs):
        return AsyncObjects(self.objects.filter)
        return await database_sync_to_async(list)(self.objects.filter(*args, **kwargs))

    def __call__(self, *args, **kwargs):
        return database_sync_to_async(self.objects)(*args, **kwargs)


# noinspection PyUnresolvedReferences
class AsyncObjectsMixin:
    _async_objects = None

    # noinspection PyArgumentList,PyMethodParameters
    @classproperty
    def async_objects(cls):
        if cls._async_objects is None:
            cls._async_objects = AsyncObjects(cls.objects)
        return cls._async_objects


class BaseModel(models.Model, AsyncObjectsMixin):
    class Meta:
        abstract = True


class PolymorphicBaseModel(PolymorphicModel, AsyncObjectsMixin):
    class Meta:
        abstract = True


class BaseClass(BaseModel):
    some_text = models.CharField(max_length=200, null=True)


class InterClass(PolymorphicBaseModel):
    foreign = models.ForeignKey('BaseClass', on_delete=models.CASCADE)


class ChildClass(InterClass):
    other_text = models.CharField(max_length=200, null=True)
