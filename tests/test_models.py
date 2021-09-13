import pytest
import torch as T
from gym.spaces import Box
from torch.autograd.grad_mode import F

from anvil.models import (
    Actor,
    ActorCritic,
    ActorCriticWithTarget,
    Critic,
    TD3ActorCritic,
)
from anvil.models.encoders import CNNEncoder, FlattenEncoder, IdentityEncoder
from anvil.models.heads import (
    ContinuousQHead,
    DeterministicPolicyHead,
    DiagGaussianPolicyHead,
    DiscreteQHead,
    ValueHead,
)
from anvil.models.torsos import MLP
from anvil.models.utils import trainable_variables


def test_mlp():
    input = T.Tensor([1, 1])
    model = MLP([2, 1])
    output = model(input)
    assert output.shape == (1,)


@pytest.mark.parametrize("encoder_class", [IdentityEncoder, FlattenEncoder])
def test_encoder(encoder_class):
    input = T.Tensor([[[2, 2], [2, 2]], [[1, 1], [1, 1]]])
    if encoder_class == CNNEncoder:
        encoder = encoder_class(Box)
    else:
        encoder = encoder_class()
    output = encoder(input)
    if isinstance(encoder, IdentityEncoder):
        assert T.equal(input, output)
    elif isinstance(encoder, FlattenEncoder):
        assert len(output.shape) == 2


@pytest.mark.parametrize("head_class", [ValueHead, ContinuousQHead, DiscreteQHead])
@pytest.mark.parametrize("input_shape", [5, (5,)])
def test_critic_head(head_class, input_shape):
    input = T.Tensor([1, 1, 1, 1, 1])
    if head_class == DiscreteQHead:
        head = head_class(input_shape=input_shape, output_shape=(2,))
    else:
        head = head_class(input_shape=input_shape)

    output = head(input)

    if head_class == DiscreteQHead:
        assert output.shape == (2,)
    else:
        assert output.shape == (1,)


@pytest.mark.parametrize(
    "head_class", [DeterministicPolicyHead, DiagGaussianPolicyHead]
)
@pytest.mark.parametrize("input_shape", [5, (5,)])
def test_actor_head(head_class, input_shape):
    input = T.Tensor([1, 1, 1, 1, 1])
    if head_class == DeterministicPolicyHead:
        head = head_class(input_shape, action_shape=2)
    elif head_class == DiagGaussianPolicyHead:
        head = head_class(input_shape, action_size=2)

    output = head(input)

    assert output.shape == (2,)


def test_critic():
    input = T.Tensor([1, 1, 1, 1, 1])
    encoder = IdentityEncoder()
    torso = MLP([5, 5])
    head = ValueHead(input_shape=5)

    critic = Critic(encoder, torso, head)

    output = critic(input)
    assert output.shape == (1,)


def test_actor():
    input = T.Tensor([1, 1, 1, 1, 1])
    encoder = IdentityEncoder()
    torso = MLP([5, 5])
    head = DeterministicPolicyHead(input_shape=5, action_shape=1)

    actor = Actor(encoder, torso, head)

    output = actor(input)
    assert output.shape == (1,)


@pytest.mark.parametrize("actor_critic_class", [ActorCritic, ActorCriticWithTarget])
@pytest.mark.parametrize("share_encoder", [True, False])
@pytest.mark.parametrize("share_torso", [True, False])
def test_actor_critic_shared_arch(actor_critic_class, share_encoder, share_torso):
    actor = Actor(
        encoder=IdentityEncoder(),
        torso=MLP([2, 3, 2]),
        head=DeterministicPolicyHead(input_shape=2, action_shape=1, activation_fn=None),
    )

    critic = Critic(
        encoder=IdentityEncoder(),
        torso=MLP([2, 2]),
        head=ValueHead(input_shape=2, activation_fn=None),
    )

    actor_critic = actor_critic_class(
        actor=actor, critic=critic, share_encoder=share_encoder, share_torso=share_torso
    )

    if not share_encoder and not share_torso:
        assert actor_critic.actor and actor_critic.critic

    else:
        assert not actor_critic.actor and not actor_critic.critic
