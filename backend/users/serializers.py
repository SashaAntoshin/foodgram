# """Кастомные сериализаторы для djoser"""
# from rest_framework import serializers
# from djoser.serializers import UserCreateSerializer, UserSerializer
# from .models import User, Follow
    

# class DjoserUserCreateSerializer(UserCreateSerializer):
#     """Сериализатор создания пользователя"""
#     password = serializers.CharField(
#         write_only=True,
#         required=True,
#         style={'input_type': 'password'}
#     )
#     class Meta(UserCreateSerializer.Meta):
#         model = User
#         fields = [
#             'id',
#             'email',
#             'username',
#             'first_name',
#             'last_name',
#             'password'
#         ]
#         extra_kwargs = {'password': {'write_only': True}}

#     def create(self, validated_data):
#         user = User(
#             email=validated_data['email'],
#             username=validated_data['username'],
#             first_name=validated_data.get('first_name', ''),
#             last_name=validated_data.get('last_name', '')
#         )
#         user.set_password(validated_data['password'])
#         user.save()
#         return user


# class DjoserUserSerializer(UserSerializer):
#     """Сериализатор пользователя для настроек Djoser"""
#     class Meta(UserSerializer.Meta):    
#         model = User
#         fields = ['id', 'email', 'username', 'first_name', 'last_name']
