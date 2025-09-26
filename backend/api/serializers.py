from rest_framework import serializers
from users.models import User, Follow
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (
    Recipe,
    IngredientsInRecipe,
    Ingredient,
    Tag,
    Favorites,
    ShoppingBasket,
)
from django.contrib.auth import get_user_model
import re
import base64
from django.core.files.base import ContentFile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели юзера"""

    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'id', 'first_name', 'last_name',
            'email', 'username', 'password'
        )
        extra_kwargs = {'password': {'write_only': True}}
        username = serializers.CharField(max_length=150)

    def get_is_subscribed(self, obj):
        request_user = self.context['request'].user
        if request_user.is_authenticated:
            if obj == request_user:
                return False
            return obj.followers.filter(user=request_user).exists()
        return False
    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        return None

    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
class UserRegistrationSerializer(serializers.ModelSerializer):
    """Регистрация, валидация username и email"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_username(self, value):
        if not re.match(r'^[\w.@+-]+\Z', value):
            raise serializers.ValidationError(
                'Разрешены только буквы, цифры и символы @/./+/-/_'
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким username уже существует.'
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует.'
            )
        return value

    def create(self, validated_data):
        """Создание пользователя с хэшированием пароля"""
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


    def validate_email(self, value):
        """Валидация email"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        from rest_framework.authtoken.models import Token
        Token.objects.get_or_create(user=user)
        return user

class RecipeShortSerializer(serializers.ModelSerializer):
    """Вспомогательный сериализатор пецептов"""
    
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

class UserLIstSerializer(serializers.ModelSerializer):
    """Сериализатор информации пользователя"""
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'is_subscribed', 'recipes',
                'recipes_count', 'avatar')

    def get_is_subscribed(self, obj):
        return False
    
    def get_recipes_count(self, obj):
        return obj.recipes.count()
    
    def get_recipes(self, obj):
        """Рецепты пользователя с ограничением через recipes_limit"""
        request = self.context.get('request')
        recipes_limit = None
        
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
        
        recipes = obj.recipes.all()
        
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        from api.serializers import RecipeShortSerializer
        return RecipeShortSerializer(recipes, many=True, context=self.context).data
    
    def get_avatar(self, obj):
        """Вернем ссылку на аватар, если он есть"""
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ('user', 'author')
        read_only_fields = ('user',)

    def validate(self, attrs):
        author = attrs.get('author')
        user = self.context['request'].user
        
        if author == user:
            raise serializers.ValidationError('Нельзя подписаться на себя')
        
        if Follow.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError('Вы уже подписаны')
        
        return attrs
    

class AvatarUpdateSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model= User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Тег"""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ингридиент"""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = IngredientsInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class Base64ImageField(serializers.ImageField):
    """Конвертация картинки для сериализатора рецептов"""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                format, imgstr = data.split(';base64,')
                ext = format.split('/')[-1]
                decoded_file = base64.b64decode(imgstr)
                file_name = f"recipe_image.{ext}"
                data = ContentFile(decoded_file, name=file_name)
                
            except Exception as e:
                raise serializers.ValidationError("Некорректный формат изображения")
        
        return super().to_internal_value(data)


            
class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserLIstSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='ingredients_amounts', many=True, read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        return False

    def get_is_in_shopping_cart(self, obj):
        return False

class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ('name', 'image', 'text', 'cooking_time', 'ingredients', 'tags')
    """Валидация тегов и ингредиентов"""

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Список ингредиентов не может быть пустым.")
        ids = [i.get('id') for i in value]
        if None in ids:
            raise serializers.ValidationError("Каждый ингредиент должен содержать id.")
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Ингредиенты не должны повторяться.")
        for ing in value:
            if 'amount' not in ing:
                raise serializers.ValidationError("Каждый ингредиент должен содержать amount.")
            if int(ing['amount']) <= 0:
                raise serializers.ValidationError("Количество должно быть больше 0.")
        existing_ids = set(Ingredient.objects.filter(id__in=ids).values_list('id', flat=True))
        missing = set(ids) - existing_ids
        if missing:
            raise serializers.ValidationError(f"Не найдены ингредиенты с id: {sorted(missing)}")
        return value

    def validate(self, data):
        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError({'tags': "Список тегов обязателен."})
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError({'tags': "Теги не должны повторяться."})
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        for ing in ingredients_data:
            IngredientsInRecipe.objects.create(
                recipe=recipe,
                ingredient_id=ing['id'],
                amount=ing['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        if ingredients_data is None:
            raise serializers.ValidationError({'ingredients': "Поле обязательно при обновлении рецепта."})
        if tags_data is None:
            raise serializers.ValidationError({'tags': "Поле обязательно при обновлении рецепта."})

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)
        if 'image' in validated_data:
            instance.image = validated_data['image']
        instance.save()

        instance.tags.set(tags_data)
        instance.ingredients_amounts.all().delete()
        for ing in ingredients_data:
            IngredientsInRecipe.objects.create(
                recipe=instance,
                ingredient_id=ing['id'],
                amount=ing['amount']
            )

        return instance


class SubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор подписок"""
    class Meta:
        model = Follow
        fields = ('user', 'author')

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError('Нельзя подписаться на себя.')
        if Follow.objects.filter(user=data['user'], author=data['author']).exists():
            raise serializers.ValidationError('Уже подписан.')
        return data


class FavoritesSerializer(serializers.ModelSerializer):
    """Сериализатор для Избранного"""
    class Meta:
        model = Favorites
        fields = ('user', 'recipe', 'added_at')


class ShopingBasketSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины"""

    class Meta:
        model = ShoppingBasket
        fields = '__all_'


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор модели Подписок"""
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
    )
    author = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all(),
    )

    class Meta:
        model = Follow
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

    def validate_author(self, value):
        """Проверка подписок"""
        user = self.context['request'].user
        if value == user:
            raise serializers.ValidationError(
                'Подписаться на себя невозможно'
            )
        if Follow.objects.filter(user=user, author=value).exists():
            raise serializers.ValidationError(
                'Вы уже подписались на этого автора ранее'
            )
        return value
