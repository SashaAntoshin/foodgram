from rest_framework import serializers
from django.core.validators import RegexValidator
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
    # avatar = Base64ImageField(required=False)
    # is_subscribed = serializers.SerializerMethodField()
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



class UserLIstSerializer(serializers.ModelSerializer):
    """Сериализатор информации пользователя"""
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        return False
    
    def get_avatar(self, obj):
        """Вернем ссылку на аватар, если он есть"""
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    

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
    """Сериализатор модели Ингридиентов в рецепте"""
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = IngredientsInRecipe
        fields = ('ingredient', 'amount')

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


            
class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True)
    # ДЛЯ ЧТЕНИЯ  
    author = UserLIstSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='ingredients_amounts', 
        many=True, 
        read_only=True
    )
    tags = TagSerializer(many=True, read_only=True, source='tags')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    # Валидации из RecipeWriteSerializer
    def validate_ingredients(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("Список ингредиентов не может быть пустым.")
        
        ingredient_ids = [ingredient['id'] for ingredient in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError("Ингредиенты не должны повторяться.")
        
        for ingredient in value:
            if 'id' not in ingredient or 'amount' not in ingredient:
                raise serializers.ValidationError("Каждый ингредиент должен содержать id и amount.")
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError("Количество ингредиента должно быть больше 0.")
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("Список тегов не может быть пустым.")
        unique_tags = list(set(value))
        if len(unique_tags) != len(value):
            raise serializers.ValidationError("Теги не должны повторяться.")
        return value

    def validate(self, data):
        errors = {}
        
        required_fields = ['image', 'ingredients', 'tags', 'name', 'text', 'cooking_time']
        for field in required_fields:
            if field not in data or data[field] in [None, '', [], {}]:
                errors[field] = ['Обязательное поле.']
        
        if errors:
            raise serializers.ValidationError(errors)
        
        ingredient_ids = [ingredient['id'] for ingredient in data['ingredients']]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            errors['ingredients'] = ['Ингредиенты не должны повторяться.']
        
        tag_ids = [tag.id for tag in data['tags']]
        if len(tag_ids) != len(set(tag_ids)):
            errors['tags'] = ['Теги не должны повторяться.']
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags")
        
        # ВАЛИДАЦИЯ: проверяем что все ингредиенты существуют
        ingredient_ids = [ingredient['id'] for ingredient in ingredients_data]
        existing_ingredients = set(
            Ingredient.objects.filter(id__in=ingredient_ids).values_list('id', flat=True)
        )
        missing_ingredients = set(ingredient_ids) - existing_ingredients
        
        if missing_ingredients:
            raise serializers.ValidationError({
                'ingredients': f'Не найдены ингредиенты с id: {sorted(missing_ingredients)}'
            })
        
        # Удаляем author из validated_data
        validated_data.pop('author', None)
        
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data
        )
        recipe.tags.set(tags_data)

        for ingredient in ingredients_data:
            IngredientsInRecipe.objects.create(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=ingredient["id"]),
                amount=ingredient["amount"]
            )
        return recipe
    
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        
        # ВАЛИДАЦИЯ ИНГРЕДИЕНТОВ ПЕРЕД ОБНОВЛЕНИЕМ
        if ingredients_data is not None:
            # Проверяем что все ингредиенты существуют
            ingredient_ids = [ingredient['id'] for ingredient in ingredients_data]
            existing_ingredients = set(
                Ingredient.objects.filter(id__in=ingredient_ids).values_list('id', flat=True)
            )
            missing_ingredients = set(ingredient_ids) - existing_ingredients
            
            if missing_ingredients:
                raise serializers.ValidationError({
                    'ingredients': f'Не найдены ингредиенты с id: {sorted(missing_ingredients)}'
                })
        
        # Удаляем read_only поля
        for field in ['author', 'ingredients_detail', 'tags_detail', 'is_favorited', 'is_in_shopping_cart']:
            validated_data.pop(field, None)
        
        # Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Обновляем теги
        if tags_data is not None:
            instance.tags.set(tags_data)
        
        # Обновляем ингредиенты
        if ingredients_data is not None:
            instance.ingredients_amounts.all().delete()
            
            for ingredient_data in ingredients_data:
                IngredientsInRecipe.objects.create(
                    recipe=instance,
                    ingredient_id=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )
        
        instance.save()
        return instance

    def get_is_favorited(self, obj):
        return False

    def get_is_in_shopping_cart(self, obj):
        return False


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
