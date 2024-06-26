import sys
from dataclasses import dataclass, field

from omegaconf import MISSING
from torch import Tensor, nn

from .modules import (
    ConvModule2d,
    ConvModule3d,
    HierarchicalConvEncoder2d,
    HierarchicalConvEncoder3d,
    IdenticalConvBlockConvParams,
    PixelWiseConv2d,
    PixelWiseConv3d,
    create_activation,
)
from .option import NetworkOption


@dataclass
class AutoEncoder2dNetworkOption(NetworkOption):
    hidden_channels: int = 64
    latent_dim: int = 4
    conv_params: list[dict[str, list[int]]] = field(
        default_factory=lambda: [
            {"kernel_size": [3], "stride": [2], "padding": [1], "output_padding": [1]},
        ]
    )
    debug_show_dim: bool = False


def create_autoencoder2d(
    out_channels: int, opt: AutoEncoder2dNetworkOption
) -> nn.Module:
    return AutoEncoder2d(
        in_channels=out_channels,
        hidden_channels=opt.hidden_channels,
        latent_dim=opt.latent_dim,
        conv_params=opt.conv_params,
        activation=opt.activation,
        debug_show_dim=opt.debug_show_dim,
    )


@dataclass
class AEEncoder2dNetworkOption(NetworkOption):
    in_channels: int = MISSING
    hidden_channels: int = MISSING
    latent_dim: int = MISSING
    conv_params: list[dict[str, list[int]]] = MISSING


def create_ae_encoder2d(opt: AEEncoder2dNetworkOption) -> nn.Module:
    return AEEncoder2d(
        opt.in_channels,
        opt.hidden_channels,
        opt.latent_dim,
        opt.conv_params,
        debug_show_dim=False,
    )


class AEEncoder2d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        debug_show_dim: bool,
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
        self.debug_show_dim = debug_show_dim

    def forward(self, x: Tensor) -> tuple[Tensor, list[Tensor]]:
        y, latent = self.cnn(x)
        z = self.bottleneck(y)

        if self.debug_show_dim:
            print("Input", x.size())
            print("Output", y.size())
            print("Latent", z.size())

        return z, latent


class AEDecoder2d(nn.Module):
    def __init__(
        self,
        out_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        debug_show_dim: bool,
    ) -> None:
        super().__init__()

        self.bottleneck = PixelWiseConv2d(
            latent_dim,
            hidden_channels,
            act_norm=True,
        )
        self.cnn = ConvModule2d(
            hidden_channels,
            out_channels,
            hidden_channels,
            conv_params,
            transpose=True,
            act_norm=False,
            debug_show_dim=debug_show_dim,
        )
        self.debug_show_dim = debug_show_dim

    def forward(self, z: Tensor) -> Tensor:
        y = self.bottleneck(z)
        x = self.cnn(y)

        if self.debug_show_dim:
            print("Latent", z.size())
            print("Output", y.size())
            print("Input", x.size())

        return x


class AutoEncoder2d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        activation: str,
        debug_show_dim: bool,
    ) -> None:
        super().__init__()

        self.encoder = AEEncoder2d(
            in_channels,
            hidden_channels,
            latent_dim,
            conv_params + [IdenticalConvBlockConvParams],
            debug_show_dim=debug_show_dim,
        )
        self.decoder = AEDecoder2d(
            in_channels,
            hidden_channels,
            latent_dim,
            conv_params[::-1],
            debug_show_dim=debug_show_dim,
        )
        self.activation = create_activation(activation)

        self.debug_show_dim = debug_show_dim

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor]:
        z, _ = self.encoder(x)
        y = self.decoder(z)
        if self.activation is not None:
            y = self.activation(y)

        if self.debug_show_dim:
            print("Input", x.size())
            print("Latent", z.size())
            print("Output", y.size())
            sys.exit(0)

        return y, z


@dataclass
class AutoEncoder3dNetworkOption(NetworkOption):
    hidden_channels: int = 64
    latent_dim: int = 4
    conv_params: list[dict[str, list[int]]] = field(
        default_factory=lambda: [
            {"kernel_size": [3], "stride": [2], "padding": [1], "output_padding": [1]},
        ]
    )
    debug_show_dim: bool = False


def create_autoencoder3d(
    out_channels: int, opt: AutoEncoder3dNetworkOption
) -> nn.Module:
    return AutoEncoder3d(
        in_channels=out_channels,
        hidden_channels=opt.hidden_channels,
        latent_dim=opt.latent_dim,
        conv_params=opt.conv_params,
        activation=opt.activation,
        debug_show_dim=opt.debug_show_dim,
    )


@dataclass
class AEEncoder3dNetworkOption(NetworkOption):
    in_channels: int = MISSING
    hidden_channels: int = MISSING
    latent_dim: int = MISSING
    conv_params: list[dict[str, list[int]]] = MISSING


def create_ae_encoder3d(opt: AEEncoder3dNetworkOption) -> nn.Module:
    return AEEncoder3d(
        opt.in_channels,
        opt.hidden_channels,
        opt.latent_dim,
        opt.conv_params,
        debug_show_dim=False,
    )


class AEEncoder3d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        debug_show_dim: bool,
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
        self.debug_show_dim = debug_show_dim

    def forward(self, x: Tensor) -> tuple[Tensor, list[Tensor]]:
        y, latent = self.cnn(x)
        z = self.bottleneck(y)

        if self.debug_show_dim:
            print("Input", x.size())
            print("Output", y.size())
            print("Latent", z.size())

        return z, latent


class AEDecoder3d(nn.Module):
    def __init__(
        self,
        out_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        debug_show_dim: bool,
    ) -> None:
        super().__init__()

        self.bottleneck = PixelWiseConv3d(
            latent_dim,
            hidden_channels,
            act_norm=True,
        )
        self.cnn = ConvModule3d(
            hidden_channels,
            out_channels,
            hidden_channels,
            conv_params,
            transpose=True,
            act_norm=False,
            debug_show_dim=debug_show_dim,
        )
        self.debug_show_dim = debug_show_dim

    def forward(self, z: Tensor) -> Tensor:
        y = self.bottleneck(z)
        x = self.cnn(y)

        if self.debug_show_dim:
            print("Latent", z.size())
            print("Output", y.size())
            print("Input", x.size())

        return x


class AutoEncoder3d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        latent_dim: int,
        conv_params: list[dict[str, list[int]]],
        activation: str,
        debug_show_dim: bool,
    ) -> None:
        super().__init__()

        self.encoder = AEEncoder3d(
            in_channels,
            hidden_channels,
            latent_dim,
            conv_params + [IdenticalConvBlockConvParams],
            debug_show_dim=debug_show_dim,
        )
        self.decoder = AEDecoder3d(
            in_channels,
            hidden_channels,
            latent_dim,
            conv_params[::-1],
            debug_show_dim=debug_show_dim,
        )
        self.activation = create_activation(activation)

        self.debug_show_dim = debug_show_dim

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor]:
        z, _ = self.encoder(x)
        y = self.decoder(z)
        if self.activation is not None:
            y = self.activation(y)

        if self.debug_show_dim:
            print("Input", x.size())
            print("Latent", z.size())
            print("Output", y.size())
            sys.exit(0)

        return y, z
