const std = @import("std");

/// 256 values
pub const Command = enum(u8) {
    discovery = 0x01,

    /// Data: generic data transfer
    /// Payload: arbitrary bytes, application-specific interpretation
    Data = 0x02,

    /// DataChunk: part of a multipart data transfer
    /// Payload: arbitrary bytes
    DataChunk = 0x03,

    /// DataEnd: final chunk of a multipart data transfer
    /// Payload: arbitrary bytes
    DataEnd = 0x04,

    /// Execute: invocation of an action
    /// Payload: actions.ActionRequest in wire format
    Execute = 0x05,

    /// Keepalive: heartbeat to prevent timeout
    /// Payload: empty
    Keepalive = 0x06,

    /// Flush: signal to flush/commit any pending operations
    /// Payload: empty
    Flush = 0x07,

    /// Close: signal to close connection/stream gracefully
    /// Payload: empty
    Close = 0x08,

    /// Unknown: used for graceful handling of unrecognized commands
    _,
};

pub const ProtocolError = error{
    InvalidCommand,
    MalformedPayload,
    PayloadTooLarge,
    BufferOverflow,
    InvalidUtf8,
} || std.mem.Allocator.Error;

pub fn parseCommand(byte: u8) Command {
    return @enumFromInt(byte);
}

pub fn validatePayload(allocator: std.mem.Allocator, cmd: Command, payload: []const u8) ProtocolError!void {
    const MAX_PAYLOAD_SIZE = 1024 * 1024;

    if (payload.len > MAX_PAYLOAD_SIZE) {
        return ProtocolError.PayloadTooLarge;
    }

    switch (cmd) {
        .Execute => {
            const MIN_ACTION_REQUEST_SIZE = 2;
            if (payload.len < MIN_ACTION_REQUEST_SIZE) {
                return ProtocolError.MalformedPayload;
            }
        },

        .discovery, .Data, .DataChunk, .DataEnd => {},

        .Flush => {
            if (payload.len > 16) {
                return ProtocolError.MalformedPayload;
            }
        },

        .Close => {
            if (payload.len > 16) {
                return ProtocolError.MalformedPayload;
            }
        },

        .Keepalive => {
            if (payload.len > 16) {
                return ProtocolError.MalformedPayload;
            }
        },

        _ => {},
    }

    _ = allocator;
}

test "parse command" {
    const cmd1 = parseCommand(0x01);
    try std.testing.expectEqual(Command.discovery, cmd1);

    const cmd_execute = parseCommand(0x05);
    try std.testing.expectEqual(Command.Execute, cmd_execute);

    const cmd2 = parseCommand(0x06);
    try std.testing.expectEqual(Command.Keepalive, cmd2);

    const cmd_unknown = parseCommand(0xFF);
    try std.testing.expectEqual(@as(u8, 0xFF), @intFromEnum(cmd_unknown));
}

test "validate Execute payload" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();

    const too_short = [_]u8{0x00} ** 1;
    try std.testing.expectError(ProtocolError.MalformedPayload, validatePayload(arena.allocator(), .Execute, &too_short));

    const min_valid = [_]u8{0x00} ** 2;
    try validatePayload(arena.allocator(), .Execute, &min_valid);
}

test "validate Flush/Close/Keepalive payload length limits" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();

    const ok = [_]u8{0} ** 16;
    try validatePayload(arena.allocator(), .Flush, &ok);
    try validatePayload(arena.allocator(), .Close, &ok);
    try validatePayload(arena.allocator(), .Keepalive, &ok);

    const too_long = [_]u8{0} ** 17;
    try std.testing.expectError(ProtocolError.MalformedPayload, validatePayload(arena.allocator(), .Flush, &too_long));
    try std.testing.expectError(ProtocolError.MalformedPayload, validatePayload(arena.allocator(), .Close, &too_long));
    try std.testing.expectError(ProtocolError.MalformedPayload, validatePayload(arena.allocator(), .Keepalive, &too_long));
}

test "validate payload rejects oversized payload regardless of command" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();

    const huge = try arena.allocator().alloc(u8, 1024 * 1024 + 1);
    try std.testing.expectError(ProtocolError.PayloadTooLarge, validatePayload(arena.allocator(), .Data, huge));
}
