# Licensed under the Apache License, Version 2.0 (the "License");
# Hierarchical Recurrent Disentangled AutoEncoder (HR-DAE)

from dataclasses import dataclass

from torch import Tensor, nn

from .functions import upsample_motion_tensor
from .modules import (
    HierarchicalConvDecoder2d,
    HierarchicalConvDecoder3d,
    HierarchicalConvEncoder2d,
    HierarchicalConvEncoder3d,
    IdenticalConvBlock2d,
    IdenticalConvBlock3d,
    IdenticalConvBlockConvParams,
    PixelWiseConv2d,
    PixelWiseConv3d,
    ResNetBranch,
    create_aggregator2d,
    create_aggregator3d,
    create_activation,
)
from .motion_encoder import (
    MotionEncoder1d,
    MotionEncoder2d,
    create_motion_encoder1d,
    create_motion_encoder2d,
)
from .r_dae import RDAE2dOption, RDAE3dOption


@dataclass
class HRDAE2dOption(RDAE2dOption):
    pass


@dataclass
class HRDAE3dOption(RDAE3dOption):
    pass


def create_hrdae2d(out_channels: int, opt: HRDAE2dOption) -> nn.Module:
    motion_encoder = create_motion_encoder1d(
        opt.latent_dim, opt.debug_show_dim, opt.motion_encoder
    )
    return HRDAE2d(
        opt.in_channels,
        out_channels,
        opt.hidden_channels,
        opt.latent_dim,
        opt.conv_params,
        motion_encoder,
        opt.activation,
        opt.aggregator,
        opt.debug_show_dim,
    )


def create_hrdae3d(out_channels: int, opt: HRDAE3dOption) -> nn.Module:
    motion_encoder = create_motion_encoder2d(
        opt.latent_dim, opt.debug_show_dim, opt.motion_encoder
    )
    return HRDAE3d(
        opt.in_channels,
        out_channels,
        opt.hidden_channels,
        opt.latent_dim,
        opt.conv_params,
        motion_encoder,
        opt.activation,
        opt.aggregator,
        opt.debug_show_dim,
    )


class HierarchicalEncoder2d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        debug_show_dim: bool = False,
    ) -> None:
        super().__init__()

        self.cnn = HierarchicalConvEncoder2d(
            in_channels,
            hidden_channels,
            hidden_channels,
            conv_params,
            act_norm=True,
            debug_show_dim=debug_show_dim,
        )
        self.bottleneck = PixelWiseConv2d(
            hidden_channels,
            latent_dim,
            act_norm=False,
        )

    def forward(self, x: Tensor) -> tuple[Tensor, list[Tensor]]:
        y, cs = self.cnn(x)
        z = self.bottleneck(y)
        return z, cs


class HierarchicalEncoder3d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        debug_show_dim: bool = False,
    ) -> None:
        super().__init__()

        self.cnn = HierarchicalConvEncoder3d(
            in_channels,
            hidden_channels,
            hidden_channels,
            conv_params,
            act_norm=True,
            debug_show_dim=debug_show_dim,
        )
        self.bottleneck = PixelWiseConv3d(
            hidden_channels,
            latent_dim,
            act_norm=False,
        )

    def forward(self, x: Tensor) -> tuple[Tensor, list[Tensor]]:
        y, cs = self.cnn(x)
        z = self.bottleneck(y)
        return z, cs


class HierarchicalDecoder2d(nn.Module):
    def __init__(
        self,
        out_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        aggregator: str,
        debug_show_dim: bool = False,
    ) -> None:
        super().__init__()

        self.aggregator = create_aggregator2d(aggregator, latent_dim, latent_dim)
        self.bottleneck = PixelWiseConv2d(
            latent_dim,
            hidden_channels,
            act_norm=True,
        )
        self.dec = HierarchicalConvDecoder2d(
            hidden_channels,
            out_channels,
            hidden_channels,
            conv_params,
            debug_show_dim,
        )
        # motion guided connection
        # (Mutual Suppression Network for Video Prediction using Disentangled Features)
        self.mgc = nn.ModuleList()
        for _ in conv_params:
            self.mgc.append(
                nn.Sequential(
                    create_aggregator2d(aggregator, hidden_channels, latent_dim),
                    ResNetBranch(
                        IdenticalConvBlock2d(hidden_channels, hidden_channels),
                        IdenticalConvBlock2d(
                            hidden_channels, hidden_channels, act_norm=False
                        ),
                    ),
                    nn.GroupNorm(2, hidden_channels),
                    nn.LeakyReLU(0.2, inplace=True),
                )
            )

    def forward(self, m: Tensor, c: Tensor, cs: list[Tensor]) -> Tensor:
        assert len(self.mgc) == len(cs)

        x = self.aggregator((c, upsample_motion_tensor(m, c)))
        for i, mgc in enumerate(self.mgc):
            cs[i] = mgc((cs[i], upsample_motion_tensor(m, cs[i])))

        x = self.bottleneck(x)
        return self.dec(x, cs)


class HierarchicalDecoder3d(nn.Module):
    def __init__(
        self,
        out_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        aggregator: str,
        debug_show_dim: bool = False,
    ) -> None:
        super().__init__()

        self.aggregator = create_aggregator3d(aggregator, latent_dim, latent_dim)
        self.bottleneck = PixelWiseConv3d(
            latent_dim,
            hidden_channels,
            act_norm=True,
        )
        self.dec = HierarchicalConvDecoder3d(
            hidden_channels,
            out_channels,
            hidden_channels,
            conv_params,
            debug_show_dim,
        )
        # motion guided connection
        # (Mutual Suppression Network for Video Prediction using Disentangled Features)
        self.mgc = nn.ModuleList()
        for _ in conv_params:
            self.mgc.append(
                nn.Sequential(
                    create_aggregator3d(aggregator, hidden_channels, latent_dim),
                    ResNetBranch(
                        IdenticalConvBlock3d(hidden_channels, hidden_channels),
                        IdenticalConvBlock3d(
                            hidden_channels, hidden_channels, act_norm=False
                        ),
                    ),
                    nn.GroupNorm(2, hidden_channels),
                    nn.LeakyReLU(0.2, inplace=True),
                )
            )

    def forward(self, m: Tensor, c: Tensor, cs: list[Tensor]) -> Tensor:
        assert len(self.mgc) == len(cs)

        x = self.aggregator((c, upsample_motion_tensor(m, c)))
        for i, mgc in enumerate(self.mgc):
            cs[i] = mgc((cs[i], upsample_motion_tensor(m, cs[i])))

        x = self.bottleneck(x)
        return self.dec(x, cs)


class HRDAE2d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        motion_encoder: MotionEncoder1d,
        activation: str,
        aggregator: str,
        debug_show_dim: bool = False,
    ) -> None:
        super().__init__()
        self.content_encoder = HierarchicalEncoder2d(
            in_channels,
            hidden_channels,
            latent_dim,
            conv_params + [IdenticalConvBlockConvParams],
            debug_show_dim,
        )
        self.motion_encoder = motion_encoder
        self.decoder = HierarchicalDecoder2d(
            out_channels,
            hidden_channels,
            latent_dim,
            conv_params[::-1],
            aggregator,
            debug_show_dim,
        )
        self.activation = create_activation(activation)

    def forward(
        self,
        x_1d: Tensor,
        x_2d_0: Tensor,
        x_1d_0: Tensor | None = None,
    ) -> Tensor:
        c, cs = self.content_encoder(x_2d_0)
        m = self.motion_encoder(x_1d, x_1d_0)
        b, t, c_, h = m.size()
        m = m.reshape(b * t, c_, h)
        c = c.repeat(t, 1, 1, 1)
        cs = [c_.repeat(t, 1, 1, 1) for c_ in cs]
        y = self.decoder(m, c, cs[::-1])
        _, c_, h, w = y.size()
        y = y.reshape(b, t, c_, h, w)
        if self.activation is not None:
            y = self.activation(y)
        return y


class HRDAE3d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        motion_encoder: MotionEncoder2d,
        activation: str,
        aggregator: str,
        debug_show_dim: bool = False,
    ) -> None:
        super().__init__()
        self.content_encoder = HierarchicalEncoder3d(
            in_channels,
            hidden_channels,
            latent_dim,
            conv_params + [IdenticalConvBlockConvParams],
            debug_show_dim,
        )
        self.motion_encoder = motion_encoder
        self.decoder = HierarchicalDecoder3d(
            out_channels,
            hidden_channels,
            latent_dim,
            conv_params[::-1],
            aggregator,
            debug_show_dim,
        )
        self.activation = create_activation(activation)

    def forward(
        self,
        x_2d: Tensor,
        x_3d_0: Tensor,
        x_2d_0: Tensor | None = None,
    ) -> Tensor:
        c, cs = self.content_encoder(x_3d_0)
        m = self.motion_encoder(x_2d, x_2d_0)
        b, t, c_, h, w = m.size()
        m = m.reshape(b * t, c_, h, w)
        c = c.repeat(t, 1, 1, 1, 1)
        cs = [c_.repeat(t, 1, 1, 1, 1) for c_ in cs]
        y = self.decoder(m, c, cs[::-1])
        _, c_, d, h, w = y.size()
        y = y.reshape(b, t, c_, d, h, w)
        if self.activation is not None:
            y = self.activation(y)
        return y
