from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager customizado para o modelo User"""
    
    def create_user(self, email, telefone, nome, password=None, **extra_fields):
        """Cria e salva um usuário comum"""
        if not email:
            raise ValueError('O email é obrigatório')
        if not telefone:
            raise ValueError('O telefone é obrigatório')
        
        email = self.normalize_email(email)
        user = self.model(email=email, telefone=telefone, nome=nome, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, telefone, nome, password=None, **extra_fields):
        """Cria e salva um superusuário"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser deve ter is_superuser=True.')
        
        return self.create_user(email, telefone, nome, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Modelo de usuário customizado"""
    
    email = models.EmailField('Email', unique=True, max_length=255)
    telefone = models.CharField('Telefone', max_length=20, unique=True)
    nome = models.CharField('Nome', max_length=255)
    
    is_active = models.BooleanField('Ativo', default=True)
    is_staff = models.BooleanField('Staff', default=False)
    must_change_password = models.BooleanField('Trocar senha no primeiro login', default=False)
    
    created_at = models.DateTimeField('Criado em', default=timezone.now)

    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['telefone', 'nome']
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return self.nome
    
    def get_short_name(self):
        return self.nome.split()[0] if self.nome else self.email
